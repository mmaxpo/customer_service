from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from fastapi.encoders import jsonable_encoder

from app.domains.customer_service.services.chat_service import (
    CustomerChatService,
)
from app.domains.customer_service.services.support.commerce.commerce_order import (
    CommerceOrder,
)
from app.domains.customer_service.services.support.commerce.customer_support_commerce_context import (
    CustomerSupportCommerceContextService,
)
from app.domains.customer_service.services.support.objective.customer_support_intake import (
    CustomerSupportIntakeService,
)
from app.domains.customer_service.services.support.objective.customer_support_objective import (
    CustomerSupportObjective,
    CustomerSupportObjectiveInterpreter,
)
from app.domains.customer_service.services.support.resolution.customer_support_resolution import (
    CustomerSupportClarificationResolver,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    CustomerSupportReviewPlanBuilder,
)
from app.domains.customer_service.services.support.planning.customer_support_review_workflow import (
    CustomerSupportReviewWorkflowBuilder,
)
from app.platform.jobs.service import JobService


@dataclass(frozen=True)
class CustomerSupportOrchestrationResult:
    """
    Result of customer-service cognitive intake/orchestration.

    handled=False means the message was not claimed by this domain
    orchestration path and may continue to normal/user workflow dispatch.
    """

    handled: bool
    support_intake: dict | None = None
    dispatch_skip_reason: str | None = None


class CustomerSupportOrchestrationService:
    """
    Coordinate provider-neutral customer-support objectives with durable
    execution assets.

    Responsibilities:
    - continue persisted clarification state;
    - interpret new support objectives;
    - obtain normalized commerce context when required;
    - produce customer clarification;
    - build guarded human-review plans;
    - enqueue durable approval workflows.

    This service does not commit the database transaction. HTTP transport,
    public-ingress replay, event publication, and fallback workflow dispatch
    remain outside this boundary.
    """

    def __init__(
        self,
        *,
        db,
        chat_service: CustomerChatService,
        commerce_context: CustomerSupportCommerceContextService,
    ):
        self.db = db
        self.chat_service = chat_service
        self.commerce_context = commerce_context

    async def handle(
        self,
        *,
        user_id,
        session,
        message,
    ) -> CustomerSupportOrchestrationResult:
        pending = await self.chat_service.get_pending_support_objective(
            session=session,
        )

        pending_status = pending.get("status") if isinstance(pending, dict) else None

        if pending_status == "awaiting_order_ref":
            return await self._continue_missing_order_ref(
                user_id=user_id,
                session=session,
                message=message,
                pending=pending,
            )

        if pending_status == "awaiting_customer":
            return await self._continue_pending(
                user_id=user_id,
                session=session,
                message=message,
                pending=pending,
            )

        return await self._handle_new_message(
            user_id=user_id,
            session=session,
            message=message,
        )

    async def _continue_missing_order_ref(
        self,
        *,
        user_id,
        session,
        message,
        pending: dict,
    ) -> CustomerSupportOrchestrationResult:
        supplied = CustomerSupportObjectiveInterpreter().interpret(message.content)

        if supplied.order_ref is None:
            assistant_message = await self.chat_service.add_ai_message(
                session_id=session.id,
                content=(
                    "I still need the order number to continue this "
                    "request. Nothing on your order has been changed."
                ),
            )

            await self.chat_service.add_inbox_ai_message_for_chat_session(
                session=session,
                chat_message=assistant_message,
            )

            updated_pending = {
                **pending,
                "status": "awaiting_order_ref",
                "latest_customer_message_id": str(message.id),
                "clarification_message_id": str(assistant_message.id),
            }

            await self.chat_service.save_pending_support_objective(
                session=session,
                pending=updated_pending,
            )

            return CustomerSupportOrchestrationResult(
                handled=True,
                dispatch_skip_reason=("pending_support_objective_awaiting_order_ref"),
                support_intake={
                    "handled": True,
                    "continued": True,
                    "requires_clarification": True,
                    "mutation_allowed": False,
                    "objective": pending["objective"],
                    "clarification_message_id": str(assistant_message.id),
                    "pending_status": "awaiting_order_ref",
                },
            )

        objective = CustomerSupportObjective.model_validate(
            pending["objective"]
        ).model_copy(
            update={
                "order_ref": supplied.order_ref,
            }
        )

        commerce_read = await self.commerce_context.get_order(
            user_id=user_id,
            order_ref=supplied.order_ref,
        )

        if not commerce_read.found or commerce_read.order is None:
            return await self._handle_order_not_found(
                session=session,
                message=message,
                objective=objective,
                order_ref=supplied.order_ref,
                customer_safe_note=commerce_read.customer_safe_note,
                continued=True,
            )

        commerce_order = commerce_read.order

        if objective.requires_clarification:
            line_items = [
                item.model_dump(mode="json") for item in commerce_order.line_items
            ]

            from app.domains.customer_service.services.support.objective.customer_support_clarification import (
                CustomerSupportClarificationService,
            )

            clarification = CustomerSupportClarificationService().build(
                objective=objective,
                line_items=line_items,
            )

            clarification_message = clarification.customer_message

            if not clarification_message:
                raise RuntimeError(
                    "Support objective required clarification "
                    "but generated no customer message"
                )

            assistant_message = await self.chat_service.add_ai_message(
                session_id=session.id,
                content=clarification_message,
            )

            await self.chat_service.add_inbox_ai_message_for_chat_session(
                session=session,
                chat_message=assistant_message,
            )

            updated_pending = {
                **pending,
                "status": "awaiting_customer",
                "objective": objective.model_dump(mode="json"),
                "order": commerce_order.model_dump(mode="json"),
                "latest_customer_message_id": str(message.id),
                "clarification_message_id": str(assistant_message.id),
            }

            await self.chat_service.save_pending_support_objective(
                session=session,
                pending=updated_pending,
            )

            return CustomerSupportOrchestrationResult(
                handled=True,
                dispatch_skip_reason=("pending_support_objective_order_ref_resolved"),
                support_intake={
                    "handled": True,
                    "continued": True,
                    "requires_clarification": True,
                    "mutation_allowed": False,
                    "objective": objective.model_dump(mode="json"),
                    "clarification_message_id": str(assistant_message.id),
                    "pending_status": "awaiting_customer",
                },
            )

        review_plan_id = self._review_plan_id(
            session_id=session.id,
            original_message_id=pending["original_message_id"],
        )

        review_plan = CustomerSupportReviewPlanBuilder().build(
            objective=objective,
            order=commerce_order,
            source_objective_version=pending.get(
                "version",
                1,
            ),
        )

        review_workflow_job = await self._enqueue_review_workflow(
            user_id=user_id,
            session=session,
            review_plan_id=review_plan_id,
            review_plan=review_plan,
            customer_message=message.content,
        )

        assistant_message = await self.chat_service.add_ai_message(
            session_id=session.id,
            content=(
                f"Thanks. I've passed your request for order {review_plan.order_ref} "
                "to our team. They'll review it and reply here. "
                "Nothing on your order has been changed yet."
            ),
        )

        await self.chat_service.add_inbox_ai_message_for_chat_session(
            session=session,
            chat_message=assistant_message,
        )

        updated_pending = {
            **pending,
            "status": "ready_for_review",
            "objective": objective.model_dump(mode="json"),
            "order": commerce_order.model_dump(mode="json"),
            "latest_customer_message_id": str(message.id),
            "resolution_message_id": str(assistant_message.id),
            "review_plan_id": review_plan_id,
            "review_plan": review_plan.model_dump(mode="json"),
            "review_workflow_job_id": str(review_workflow_job.id),
            "review_workflow_job_status": str(review_workflow_job.status),
        }

        await self.chat_service.save_pending_support_objective(
            session=session,
            pending=updated_pending,
        )

        return CustomerSupportOrchestrationResult(
            handled=True,
            dispatch_skip_reason=("pending_support_objective_order_ref_resolved"),
            support_intake={
                "handled": True,
                "continued": True,
                "requires_clarification": False,
                "mutation_allowed": False,
                "objective": objective.model_dump(mode="json"),
                "resolution_message_id": str(assistant_message.id),
                "pending_status": "ready_for_review",
                "review_plan_id": review_plan_id,
                "review_plan": review_plan.model_dump(mode="json"),
                "review_workflow_job_id": str(review_workflow_job.id),
                "review_workflow_job_status": str(review_workflow_job.status),
            },
        )

    async def _continue_pending(
        self,
        *,
        user_id,
        session,
        message,
        pending: dict,
    ) -> CustomerSupportOrchestrationResult:
        persisted_objective = CustomerSupportObjective.model_validate(
            pending["objective"]
        )
        persisted_order = CommerceOrder.model_validate(pending["order"])

        resolution = CustomerSupportClarificationResolver().resolve(
            message=message.content,
            objective=persisted_objective,
            order=persisted_order,
        )

        review_plan = None
        review_plan_id = None
        review_workflow_job = None

        if resolution.status == "ready_for_review":
            review_plan_id = self._review_plan_id(
                session_id=session.id,
                original_message_id=pending["original_message_id"],
            )

            review_plan = CustomerSupportReviewPlanBuilder().build(
                objective=resolution.objective,
                order=persisted_order,
                source_objective_version=pending.get(
                    "version",
                    1,
                ),
            )

            review_workflow_job = await self._enqueue_review_workflow(
                user_id=user_id,
                session=session,
                review_plan_id=review_plan_id,
                review_plan=review_plan,
                customer_message=message.content,
            )

            continuation_message = self._completed_complex_message(
                objective=resolution.objective,
                order=persisted_order,
            )
        else:
            continuation_message = self._remaining_clarification_message(
                resolution.unresolved_fields
            )

        assistant_message = await self.chat_service.add_ai_message(
            session_id=session.id,
            content=continuation_message,
        )

        await self.chat_service.add_inbox_ai_message_for_chat_session(
            session=session,
            chat_message=assistant_message,
        )

        updated_pending = {
            **pending,
            "status": resolution.status,
            "objective": resolution.objective.model_dump(mode="json"),
            "resolution_message_id": str(assistant_message.id),
            "latest_customer_message_id": str(message.id),
        }

        if review_plan is not None:
            updated_pending["review_plan_id"] = review_plan_id
            updated_pending["review_plan"] = review_plan.model_dump(mode="json")

            if review_workflow_job is not None:
                updated_pending["review_workflow_job_id"] = str(review_workflow_job.id)
                updated_pending["review_workflow_job_status"] = str(
                    review_workflow_job.status
                )

        await self.chat_service.save_pending_support_objective(
            session=session,
            pending=updated_pending,
        )

        return CustomerSupportOrchestrationResult(
            handled=True,
            dispatch_skip_reason=("pending_support_objective_continuation"),
            support_intake={
                "handled": True,
                "continued": True,
                "requires_clarification": (resolution.objective.requires_clarification),
                "mutation_allowed": False,
                "objective": resolution.objective.model_dump(mode="json"),
                "resolution_message_id": str(assistant_message.id),
                "pending_status": resolution.status,
                "review_plan_id": review_plan_id,
                "review_plan": (
                    review_plan.model_dump(mode="json")
                    if review_plan is not None
                    else None
                ),
                "review_workflow_job_id": (
                    str(review_workflow_job.id)
                    if review_workflow_job is not None
                    else None
                ),
                "review_workflow_job_status": (
                    str(review_workflow_job.status)
                    if review_workflow_job is not None
                    else None
                ),
            },
        )

    async def _handle_new_message(
        self,
        *,
        user_id,
        session,
        message,
    ) -> CustomerSupportOrchestrationResult:
        objective = CustomerSupportObjectiveInterpreter().interpret(message.content)

        if not objective.requested_actions:
            return CustomerSupportOrchestrationResult(
                handled=False,
            )

        # A question about how returns or refunds work (no order named) is
        # answered from the help articles by the chat workflow, not treated
        # as a request to act on an order.
        if objective.order_ref is None and _is_policy_question(message.content):
            return CustomerSupportOrchestrationResult(
                handled=False,
            )

        # Actionable support objectives belong to the cognitive support
        # domain. They must not fall through to keyword/user workflow
        # dispatch merely because they are simple.
        if objective.order_ref is None:
            assistant_message = await self.chat_service.add_ai_message(
                session_id=session.id,
                content=(
                    "I can help with that. What is your order number? "
                    "Nothing on your order has been changed."
                ),
            )

            await self.chat_service.add_inbox_ai_message_for_chat_session(
                session=session,
                chat_message=assistant_message,
            )

            pending = {
                "version": 1,
                "status": "awaiting_order_ref",
                "original_message_id": str(message.id),
                "clarification_message_id": str(assistant_message.id),
                "objective": objective.model_dump(mode="json"),
            }

            await self.chat_service.save_pending_support_objective(
                session=session,
                pending=pending,
            )

            return CustomerSupportOrchestrationResult(
                handled=True,
                dispatch_skip_reason="support_objective_missing_order_ref",
                support_intake={
                    "handled": True,
                    "requires_clarification": True,
                    "mutation_allowed": False,
                    "objective": objective.model_dump(mode="json"),
                    "clarification_message_id": str(assistant_message.id),
                    "pending_status": "awaiting_order_ref",
                },
            )

        commerce_read = await self.commerce_context.get_order(
            user_id=user_id,
            order_ref=objective.order_ref,
        )

        if not commerce_read.found or commerce_read.order is None:
            return await self._handle_order_not_found(
                session=session,
                message=message,
                objective=objective,
                order_ref=objective.order_ref,
                customer_safe_note=commerce_read.customer_safe_note,
                continued=False,
            )

        commerce_order = commerce_read.order

        intake_result = CustomerSupportIntakeService().assess(
            message=message.content,
            order=commerce_order,
        )

        if intake_result.clarification.required:
            clarification_message = intake_result.clarification.customer_message

            if not clarification_message:
                raise RuntimeError(
                    "Support intake required clarification "
                    "but generated no customer message"
                )

            assistant_message = await self.chat_service.add_ai_message(
                session_id=session.id,
                content=clarification_message,
            )

            await self.chat_service.add_inbox_ai_message_for_chat_session(
                session=session,
                chat_message=assistant_message,
            )

            pending = {
                "version": 1,
                "status": "awaiting_customer",
                "original_message_id": str(message.id),
                "clarification_message_id": str(assistant_message.id),
                "order": commerce_order.model_dump(mode="json"),
                "objective": intake_result.objective.model_dump(mode="json"),
            }

            await self.chat_service.save_pending_support_objective(
                session=session,
                pending=pending,
            )

            return CustomerSupportOrchestrationResult(
                handled=True,
                dispatch_skip_reason=("support_objective_requires_clarification"),
                support_intake={
                    "handled": True,
                    "requires_clarification": True,
                    "mutation_allowed": False,
                    "objective": (intake_result.objective.model_dump(mode="json")),
                    "clarification_message_id": str(assistant_message.id),
                    "pending_status": "awaiting_customer",
                },
            )

        review_plan_id = self._review_plan_id(
            session_id=session.id,
            original_message_id=message.id,
        )

        review_plan = CustomerSupportReviewPlanBuilder().build(
            objective=intake_result.objective,
            order=commerce_order,
            source_objective_version=1,
        )

        review_workflow_job = await self._enqueue_review_workflow(
            user_id=user_id,
            session=session,
            review_plan_id=review_plan_id,
            review_plan=review_plan,
            customer_message=message.content,
        )

        assistant_message = await self.chat_service.add_ai_message(
            session_id=session.id,
            content=(
                f"Thanks. I've passed your request for order {review_plan.order_ref} "
                "to our team. They'll review it and reply here. "
                "Nothing on your order has been changed yet."
            ),
        )

        await self.chat_service.add_inbox_ai_message_for_chat_session(
            session=session,
            chat_message=assistant_message,
        )

        completed = {
            "version": 1,
            "status": "ready_for_review",
            "original_message_id": str(message.id),
            "resolution_message_id": str(assistant_message.id),
            "order": commerce_order.model_dump(mode="json"),
            "objective": intake_result.objective.model_dump(mode="json"),
            "review_plan_id": review_plan_id,
            "review_plan": review_plan.model_dump(mode="json"),
            "review_workflow_job_id": str(review_workflow_job.id),
            "review_workflow_job_status": str(review_workflow_job.status),
        }

        await self.chat_service.save_pending_support_objective(
            session=session,
            pending=completed,
        )

        return CustomerSupportOrchestrationResult(
            handled=True,
            dispatch_skip_reason="support_objective_ready_for_review",
            support_intake={
                "handled": True,
                "requires_clarification": False,
                "mutation_allowed": False,
                "objective": intake_result.objective.model_dump(mode="json"),
                "resolution_message_id": str(assistant_message.id),
                "pending_status": "ready_for_review",
                "review_plan_id": review_plan_id,
                "review_plan": review_plan.model_dump(mode="json"),
                "review_workflow_job_id": str(review_workflow_job.id),
                "review_workflow_job_status": str(review_workflow_job.status),
            },
        )

    async def _enqueue_review_workflow(
        self,
        *,
        user_id,
        session,
        review_plan_id: str,
        review_plan,
        customer_message: str,
    ):
        builder = CustomerSupportReviewWorkflowBuilder()
        # Runs are shown in the Inbox and Live by inbox conversation, which is
        # not the chat session id.
        bridge = await self.chat_service.ensure_inbox_bridge_for_session(
            session=session,
        )
        conversation_id = str(bridge.conversation_id)

        workflow = builder.build(
            review_plan_id=review_plan_id,
            review_plan=review_plan,
        )

        return await JobService(self.db).enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload=jsonable_encoder(
                {
                    "workflow": workflow,
                    "message": (
                        "Customer support resolution "
                        f"ready for review: {review_plan_id}"
                    ),
                    "thread_id": conversation_id,
                    "extras": {
                        "customer_service": True,
                        "session_id": str(session.id),
                        "conversation_id": conversation_id,
                        "customer_message": customer_message,
                        "support_review": (
                            builder.support_review_extras(
                                review_plan_id=review_plan_id,
                                review_plan=review_plan,
                            )
                        ),
                        "event": {
                            "event_type": ("customer_support.review_requested"),
                            "source": "customer_service.chat",
                            "payload": {
                                "session_id": str(session.id),
                                "review_plan_id": review_plan_id,
                                "conversation_id": conversation_id,
                            },
                        },
                    },
                }
            ),
            idempotency_key=(
                builder.workflow_job_idempotency_key(
                    review_plan_id=review_plan_id,
                )
            ),
            max_attempts=3,
            commit=False,
        )

    async def _handle_order_not_found(
        self,
        *,
        session,
        message,
        objective: CustomerSupportObjective,
        order_ref: str,
        customer_safe_note: str | None,
        continued: bool,
    ) -> CustomerSupportOrchestrationResult:
        assistant_message = await self.chat_service.add_ai_message(
            session_id=session.id,
            content=(
                customer_safe_note
                or (
                    f"I couldn't find order {order_ref}. "
                    "Please check the order number and try again."
                )
            ),
        )

        await self.chat_service.add_inbox_ai_message_for_chat_session(
            session=session,
            chat_message=assistant_message,
        )

        pending = {
            "version": 1,
            "status": "awaiting_order_ref",
            "original_message_id": str(message.id),
            "clarification_message_id": str(assistant_message.id),
            "objective": objective.model_copy(update={"order_ref": None}).model_dump(
                mode="json"
            ),
        }

        await self.chat_service.save_pending_support_objective(
            session=session,
            pending=pending,
        )

        return CustomerSupportOrchestrationResult(
            handled=True,
            dispatch_skip_reason="support_order_not_found",
            support_intake={
                "handled": True,
                "continued": continued,
                "requires_clarification": True,
                "mutation_allowed": False,
                "objective": pending["objective"],
                "clarification_message_id": str(assistant_message.id),
                "pending_status": "awaiting_order_ref",
                "order_not_found": True,
                "order_ref": order_ref,
            },
        )

    @staticmethod
    def _review_plan_id(
        *,
        session_id,
        original_message_id,
    ) -> str:
        return str(
            uuid5(
                NAMESPACE_URL,
                (f"tajeran:{session_id}:{original_message_id}:support-review-plan:v1"),
            )
        )

    @staticmethod
    def _remaining_clarification_message(
        unresolved_fields,
    ) -> str:
        missing_labels = {
            "refund_item": "which item should be refunded",
            "replacement_item": "which item should be replaced",
            "replacement_address": ("the replacement shipping address"),
        }

        remaining = [missing_labels[item.value] for item in unresolved_fields]

        return (
            "I still need "
            + ", ".join(remaining)
            + ". Nothing on your order has been changed."
        )

    @staticmethod
    def _completed_complex_message(
        *,
        objective: CustomerSupportObjective,
        order: CommerceOrder,
    ) -> str:
        refund_item_id = objective.item_assignments["refund_item"]
        replacement_item_id = objective.item_assignments["replacement_item"]

        item_by_id = {
            (
                item.provider_item_id
                or item.variant_id
                or item.product_id
                or item.title
            ): item
            for item in order.line_items
        }

        refund_item = item_by_id.get(refund_item_id)
        replacement_item = item_by_id.get(replacement_item_id)

        refund_label = (
            refund_item.title if refund_item is not None else str(refund_item_id)
        )
        replacement_label = (
            replacement_item.title
            if replacement_item is not None
            else str(replacement_item_id)
        )

        address = (objective.replacement_address or {}).get("formatted")

        return (
            f"I have confirmed the request to refund "
            f"{refund_label}, replace {replacement_label}, "
            f"and send the replacement to {address}. "
            "Our team will review it and reply here. "
            "Nothing on your order has been changed yet."
        )


_POLICY_QUESTION_OPENERS = (
    "how do i",
    "how can i",
    "how does",
    "how long",
    "when do i",
    "when will i",
    "what is your",
    "what's your",
    "what are your",
    "can i ",
    "do you ",
    "policy",
)


def _is_policy_question(content: str) -> bool:
    lowered = content.lower()
    return any(opener in lowered for opener in _POLICY_QUESTION_OPENERS)


__all__ = [
    "CustomerSupportOrchestrationResult",
    "CustomerSupportOrchestrationService",
]
