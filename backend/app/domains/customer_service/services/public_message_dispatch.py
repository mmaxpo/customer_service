"""
Decide how a public website-chat message should be answered.

The HTTP adapter persists the ingress message and event. This service owns the
support-orchestration, human handoff, and workflow-dispatch decision that
follows those writes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domains.customer_service.services.event_subscriptions import (
    CustomerServiceEventSubscriptionService,
)
from app.domains.customer_service.providers.commerce_defaults import (
    build_default_commerce_order_adapter_registry,
)
from app.domains.customer_service.services.support.commerce.customer_support_commerce_context import (
    CustomerSupportCommerceContextService,
)
from app.domains.customer_service.services.support.customer_support_orchestration import (
    CustomerSupportOrchestrationResult,
    CustomerSupportOrchestrationService,
)
from app.domains.customer_service.workflows.message_classifier import (
    CustomerServiceMessageClassifier,
)


# Topics a person must handle; no workflow answers them.
SAFE_HANDOFF_INTENTS = {"cancellation", "damaged_product"}


@dataclass(frozen=True)
class PublicMessageDispatchResult:
    orchestration: CustomerSupportOrchestrationResult
    support_intake: dict | None
    workflow_dispatch: dict


class PublicMessageDispatchService:
    """Choose support orchestration, human handoff, or matching workflows."""

    def __init__(self, *, db, chat_service, runtime_services):
        self.db = db
        self.chat_service = chat_service
        self.runtime_services = runtime_services

    async def decide(self, *, user_id, session, message, inbox_message, event):
        orchestration = await self._run_orchestration(
            user_id=user_id,
            session=session,
            message=message,
            inbox_message=inbox_message,
        )
        classification = CustomerServiceMessageClassifier().classify(message.content)
        orchestration = await self._protect_risky_intent(
            session=session,
            intent=classification.intent,
            orchestration=orchestration,
        )

        if orchestration.handled:
            workflow_dispatch = self._skipped_dispatch(orchestration, classification)
        else:
            workflow_dispatch = await CustomerServiceEventSubscriptionService(
                self.db
            ).enqueue_matching_workflows_for_event(
                event=event,
                commit=False,
            )

        return PublicMessageDispatchResult(
            orchestration=orchestration,
            support_intake=orchestration.support_intake,
            workflow_dispatch=workflow_dispatch,
        )

    async def _run_orchestration(
        self, *, user_id, session, message, inbox_message
    ) -> CustomerSupportOrchestrationResult:
        # Once a team member has replied, the conversation is theirs: no
        # automated reply until the case is resolved.
        if inbox_message is not None and await self.chat_service.team_member_is_handling(
            conversation_id=inbox_message.conversation_id
        ):
            return CustomerSupportOrchestrationResult(
                handled=True,
                dispatch_skip_reason="team_member_is_handling",
            )

        return await CustomerSupportOrchestrationService(
            db=self.db,
            chat_service=self.chat_service,
            commerce_context=CustomerSupportCommerceContextService(
                capabilities=self.runtime_services.capabilities,
                commerce_adapters=build_default_commerce_order_adapter_registry(),
            ),
        ).handle(
            user_id=user_id,
            session=session,
            message=message,
        )

    async def _protect_risky_intent(
        self, *, session, intent: str, orchestration: CustomerSupportOrchestrationResult
    ) -> CustomerSupportOrchestrationResult:
        # Do not let a merchant's single attached order-status workflow answer a
        # risky request such as cancellation or a damaged-item report. Those
        # intents must remain in the human-review lane until their dedicated
        # approval workflow is selected. Give the customer a truthful handoff
        # instead of running an unrelated workflow.
        if orchestration.handled or intent not in SAFE_HANDOFF_INTENTS:
            return orchestration

        handoff_message = await self.chat_service.add_ai_message(
            session_id=session.id,
            content=(
                "Thanks. I've passed your request to our team. They'll review it "
                "and reply here. Nothing on your order has been changed yet."
            ),
        )
        await self.chat_service.add_inbox_ai_message_for_chat_session(
            session=session,
            chat_message=handoff_message,
        )
        return replace(
            orchestration,
            handled=True,
            dispatch_skip_reason="risky_intent_requires_human_review",
        )

    @staticmethod
    def _skipped_dispatch(
        orchestration: CustomerSupportOrchestrationResult, classification
    ) -> dict:
        return {
            "matched": 0,
            "filter_matched": 0,
            "selected": 0,
            "enqueued": [],
            "skipped": [{"reason": orchestration.dispatch_skip_reason}],
            "classification": classification.model_dump(),
        }
