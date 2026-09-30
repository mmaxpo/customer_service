from fastapi import HTTPException

from app.models.models import PlatformJob

from app.domains.customer_service.repositories.audit_logs import AuditLogRepository
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.repositories.suggested_actions import (
    SuggestedActionRepository,
)
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.conversations import (
    ConversationMessageCreate,
    SenderType,
)
from app.domains.customer_service.schemas.tickets import TicketUpdate
from app.domains.customer_service.services.assignment import AssignmentService
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)
from app.domains.customer_service.services.knowledge import (
    CustomerServiceKnowledgeService,
)
from app.domains.customer_service.services.inbox import InboxService
from app.domains.customer_service.services.macros import MacroService
from app.domains.customer_service.services.sla import SLAService
from app.domains.customer_service.services.tags import ConversationTagService
from app.domains.customer_service.services.reply_quality import ReplyQualityService
from app.domains.customer_service.services.shopify import ShopifyService
from app.domains.customer_service.services.ai_reply_composer import (
    CustomerServiceAIReplyComposer,
)
from app.domains.customer_service.services.shopify_action_workflows import (
    ShopifyActionWorkflowService,
)
from app.domains.customer_service.services.action_observability import (
    observe_suggested_action_execution,
)
from app.domains.customer_service.schemas.autopilot import AutopilotEvaluationRequest
from app.domains.customer_service.schemas.commercial import ReplySendRequest
from app.domains.customer_service.services.autopilot import (
    CustomerServiceAutopilotService,
)
from app.domains.customer_service.services.messaging import (
    CustomerServiceMessagingService,
)


class SuggestedActionService:
    def __init__(self, db):
        self.db = db
        self.repo = SuggestedActionRepository(db)
        self.audit = AuditLogRepository(db)

    async def generate(self, user_id, conversation_id):
        await self.repo.supersede_open_for_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        intelligence = await ConversationIntelligenceService(self.db).analyze(
            user_id=user_id,
            conversation_id=conversation_id,
            force_refresh=True,
        )

        actions = []

        if intelligence.intent == "refund_request":
            actions.append(
                await self.repo.create(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    action_type="refund",
                    title="Start refund process",
                    description="Customer likely wants refund",
                    payload={"reason": intelligence.intent},
                    confidence=0.9,
                    status="suggested",
                    source="rule",
                )
            )

        if intelligence.sentiment == "negative":
            actions.append(
                await self.repo.create(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    action_type="escalate",
                    title="Escalate conversation",
                    description="Negative customer detected",
                    payload={"sentiment": intelligence.sentiment},
                    confidence=0.8,
                    status="suggested",
                    source="rule",
                )
            )

        if intelligence.urgency == "high":
            actions.append(
                await self.repo.create(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    action_type="assign",
                    title="Assign immediately",
                    description="Urgent conversation",
                    payload={"urgency": intelligence.urgency},
                    confidence=0.85,
                    status="suggested",
                    source="rule",
                )
            )

        order_refs = (intelligence.entities or {}).get("order_refs") or []

        primary_order_ref = order_refs[0] if order_refs else None

        if primary_order_ref:
            if intelligence.intent == "refund_request":
                actions.append(
                    await self.repo.create(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        action_type="shopify_refund",
                        title="Prepare Shopify refund",
                        description=f"Refund order {primary_order_ref}",
                        payload=await self._prepare_shopify_workflow_payload(
                            user_id=user_id,
                            action="refund",
                            order_ref=primary_order_ref,
                            reason=intelligence.intent,
                        ),
                        confidence=0.92,
                        status="suggested",
                        source="shopify",
                    )
                )

            if intelligence.intent in {
                "cancellation",
                "cancellation_request",
            }:
                actions.append(
                    await self.repo.create(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        action_type="shopify_cancel",
                        title="Prepare Shopify cancellation",
                        description=f"Cancel order {primary_order_ref}",
                        payload=await self._prepare_shopify_workflow_payload(
                            user_id=user_id,
                            action="cancel",
                            order_ref=primary_order_ref,
                            reason=intelligence.intent,
                        ),
                        confidence=0.92,
                        status="suggested",
                        source="shopify",
                    )
                )

            if intelligence.intent == "damaged_item":
                actions.append(
                    await self.repo.create(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        action_type="shopify_damaged_item",
                        title="Open damaged item case",
                        description=f"Damaged item for order {primary_order_ref}",
                        payload=await self._prepare_shopify_workflow_payload(
                            user_id=user_id,
                            action="damaged_item",
                            order_ref=primary_order_ref,
                            reason=intelligence.intent,
                        ),
                        confidence=0.90,
                        status="suggested",
                        source="shopify",
                    )
                )

            if (
                intelligence.intent == "shipping_delay"
                or self._looks_like_tracking_request(intelligence)
            ):
                actions.append(
                    await self.repo.create(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        action_type="shopify_track_order",
                        title="Check shipping status",
                        description=f"Track order {primary_order_ref}",
                        payload=await self._prepare_shopify_workflow_payload(
                            user_id=user_id,
                            action="shipping_status",
                            order_ref=primary_order_ref,
                        ),
                        confidence=0.88,
                        status="suggested",
                        source="shopify",
                    )
                )

        knowledge_action = await self._build_knowledge_reply_action(
            user_id=user_id,
            conversation_id=conversation_id,
            query=intelligence.summary,
        )

        if knowledge_action is not None:
            actions.append(knowledge_action)

        return await self._apply_autopilot(
            user_id=user_id,
            conversation_id=conversation_id,
            intelligence=intelligence,
            actions=actions,
        )

    async def _apply_autopilot(
        self, *, user_id, conversation_id, intelligence, actions
    ):
        conversation = await ConversationRepository(self.db).get_detail(
            user_id=user_id, conversation_id=conversation_id
        )
        if conversation is None:
            return actions
        autopilot = CustomerServiceAutopilotService(self.db)
        for action in actions:
            action_kind, risk = self._autopilot_action_profile(action.action_type)
            decision = await autopilot.evaluate(
                workspace_id=user_id,
                payload=AutopilotEvaluationRequest(
                    intent=intelligence.intent,
                    action_kind=action_kind,
                    risk=risk,
                    confidence=min(
                        float(action.confidence or 0),
                        float(intelligence.confidence or 0),
                    ),
                    channel=conversation.channel,
                    language=getattr(intelligence, "language", None) or "und",
                    action_type=action.action_type,
                ),
            )
            action.payload = {
                **(action.payload or {}),
                "autopilot": decision.model_dump(mode="json"),
            }
            if decision.decision == "never_automate":
                action.status = "suppressed"
            await self.repo.save(action)

            if decision.may_send and action.action_type == "reply":
                await self._auto_send_reply(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    action=action,
                )
        return actions

    async def _auto_send_reply(self, *, user_id, conversation_id, action) -> None:
        body = (action.payload or {}).get("body")
        if not body:
            return
        try:
            delivery = await CustomerServiceMessagingService(self.db).send_reply(
                workspace_id=user_id,
                actor_user_id=user_id,
                conversation_id=conversation_id,
                payload=ReplySendRequest(
                    body=body,
                    idempotency_key=f"autopilot-{action.id}",
                ),
            )
        except Exception as exc:
            action.payload = {
                **(action.payload or {}),
                "autopilot_delivery": {
                    "status": "failed",
                    "failure_type": type(exc).__name__,
                },
            }
            await self.repo.save(action)
            await self.audit.create(
                user_id=user_id,
                entity_type="suggested_action",
                entity_id=action.id,
                action="autopilot.delivery_failed",
                message="Autopilot reply delivery failed and was returned to draft",
                meta={
                    "conversation_id": str(conversation_id),
                    "failure_type": type(exc).__name__,
                },
            )
            return
        action.status = "executed"
        action.payload = {
            **(action.payload or {}),
            "autopilot_delivery": {"status": "sent", **delivery},
        }
        await self.repo.save(action)
        await self.audit.create(
            user_id=user_id,
            entity_type="suggested_action",
            entity_id=action.id,
            action="autopilot.reply_sent",
            message="Autopilot safely sent a customer reply",
            meta={
                "conversation_id": str(conversation_id),
                "message_id": delivery.get("message_id"),
            },
        )

    def _autopilot_action_profile(self, action_type: str) -> tuple[str, str]:
        if action_type == "reply":
            return "reply", "low"
        if action_type in {
            "shopify_refund",
            "shopify_cancel",
            "shopify_damaged_item",
            "close_ticket",
        }:
            return "mutation", "high"
        if action_type in {"assign", "escalate"}:
            return "routing", "medium"
        return "internal", "low"

    async def list(self, user_id, conversation_id):
        return await self.repo.list_by_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

    async def accept(self, user_id, action_id):
        action = await self._get_action(user_id, action_id)

        if action.status not in {"suggested", "rejected"}:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot accept action from status {action.status}",
            )

        action.status = "accepted"
        saved = await self.repo.save(action)

        await self.audit.create(
            user_id=user_id,
            actor_id=user_id,
            entity_type="suggested_action",
            entity_id=action.id,
            action="suggested_action.accepted",
            message=f"Suggested action accepted: {action.action_type}",
            meta={
                "conversation_id": str(action.conversation_id),
                "action_type": action.action_type,
            },
        )

        return saved

    async def reject(self, user_id, action_id):
        action = await self._get_action(user_id, action_id)

        if action.status == "executed":
            raise HTTPException(status_code=409, detail="Cannot reject executed action")

        action.status = "rejected"
        saved = await self.repo.save(action)

        await self.audit.create(
            user_id=user_id,
            actor_id=user_id,
            entity_type="suggested_action",
            entity_id=action.id,
            action="suggested_action.rejected",
            message=f"Suggested action rejected: {action.action_type}",
            meta={
                "conversation_id": str(action.conversation_id),
                "action_type": action.action_type,
            },
        )

        return saved

    async def execute(self, user_id, action_id, payload: dict | None = None):
        action = await self._get_action(user_id, action_id)

        if action.status != "accepted":
            raise HTTPException(
                status_code=409,
                detail="Action must be accepted before execution",
            )

        execution_result = await self._execute_action(
            user_id=user_id,
            action=action,
            payload=payload or {},
        )

        action.payload = {
            **(action.payload or {}),
            **(payload or {}),
            "execution_result": execution_result,
        }
        action.status = "executed"

        saved = await self.repo.save(action)

        self.db.add(
            PlatformJob(
                user_id=user_id,
                job_type="workflow.run",
                status="succeeded",
                payload={
                    "message": f"Suggested action executed: {action.title}",
                    "workflow": {"name": "Suggested action execution"},
                    "extras": {
                        "event": {
                            "event_type": "suggested_action.executed",
                            "payload": {
                                "conversation_id": str(action.conversation_id),
                                "action_id": str(action.id),
                                "action_type": action.action_type,
                                "channel": "shopify"
                                if action.action_type.startswith("shopify_")
                                else None,
                            },
                        },
                        "suggested_action": {
                            "id": str(action.id),
                            "title": action.title,
                            "description": action.description,
                            "status": action.status,
                            "source": action.source,
                            "confidence": action.confidence,
                        },
                    },
                },
                result={
                    "status": "succeeded",
                    "action_type": action.action_type,
                    "execution_result": execution_result,
                },
                attempts=1,
                max_attempts=1,
            )
        )
        await self.db.commit()

        await self.audit.create(
            user_id=user_id,
            actor_id=user_id,
            entity_type="suggested_action",
            entity_id=action.id,
            action="suggested_action.executed",
            message=f"Suggested action executed: {action.action_type}",
            meta={
                "conversation_id": str(action.conversation_id),
                "action_type": action.action_type,
                "execution_result": execution_result,
            },
        )

        return saved

    def _looks_like_tracking_request(self, intelligence) -> bool:
        text = " ".join(
            str(value or "")
            for value in [
                getattr(intelligence, "intent", None),
                getattr(intelligence, "summary", None),
                getattr(intelligence, "sentiment", None),
                getattr(intelligence, "urgency", None),
            ]
        ).lower()

        return any(
            phrase in text
            for phrase in [
                "track",
                "tracking",
                "where is my order",
                "shipping",
                "shipment",
                "delivery",
                "fulfilled",
            ]
        )

    async def _prepare_shopify_workflow_payload(
        self,
        *,
        user_id,
        action: str,
        order_ref: str,
        reason: str | None = None,
        note: str | None = None,
        new_address: dict | None = None,
    ) -> dict:
        base_payload = {
            "order_ref": order_ref,
            "reason": reason,
        }

        try:
            prepared = await ShopifyService(self.db).prepare_support_workflow(
                user_id=user_id,
                action=action,
                order_ref=order_ref,
                reason=reason,
                note=note,
                new_address=new_address,
            )
        except Exception as exc:
            base_payload["prepared_workflow_error"] = str(exc)
            return base_payload

        base_payload["prepared_workflow"] = prepared
        return base_payload

    async def suggest_shopify_actions(
        self,
        *,
        user_id,
        conversation_id,
        triage_result,
        shopify_context: dict | None,
    ):
        if not shopify_context:
            return []

        order = shopify_context.get("order") or {}
        payload = {
            "shopify_context": shopify_context,
            "triage": triage_result.model_dump(mode="json")
            if hasattr(triage_result, "model_dump")
            else {},
        }

        actions = []

        intent = getattr(triage_result, "intent", None)

        if shopify_context.get("found") and order:
            actions.append(
                await self.repo.create(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    action_type="shopify_lookup_order",
                    title="Review Shopify order",
                    description="Attach Shopify order context to this conversation.",
                    payload=payload,
                    confidence=0.92,
                    status="suggested",
                    source="shopify",
                )
            )

        if intent == "refund_request":
            actions.append(
                await self.repo.create(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    action_type="shopify_refund",
                    title="Prepare Shopify refund",
                    description="Customer appears to be requesting a refund.",
                    payload=payload,
                    confidence=0.86,
                    status="suggested",
                    source="shopify",
                )
            )

        if intent in {"shipping_status", "general"} and shopify_context.get("found"):
            actions.append(
                await self.repo.create(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    action_type="shopify_shipping_status",
                    title="Send Shopify shipping status",
                    description="Customer appears to be asking about order/shipping status.",
                    payload=payload,
                    confidence=0.84,
                    status="suggested",
                    source="shopify",
                )
            )

        return actions

    def _reply_intent_from_query(self, query: str) -> str:
        value = (query or "").lower()

        if "refund" in value or "money back" in value:
            return "refund_request"

        if "cancel" in value or "cancellation" in value:
            return "cancellation"

        if "damaged" in value or "broken" in value:
            return "damaged_item"

        if "shipping" in value or "where is" in value or "late" in value:
            return "shipping_status"

        return "general_support"

    async def _build_knowledge_reply_action(
        self,
        *,
        user_id,
        conversation_id,
        query: str,
    ):
        try:
            result = await CustomerServiceKnowledgeService(self.db).search_context(
                user_id=user_id,
                query=query,
                k=3,
            )
        except Exception:
            return None

        context = (result.get("context") or "").strip()
        hits = result.get("hits") or []

        if not context or not hits:
            return None

        composer_result = CustomerServiceAIReplyComposer().compose(
            customer_message=query,
            intelligence=type(
                "IntelligenceSnapshot",
                (),
                {
                    "intent": self._reply_intent_from_query(query),
                    "sentiment": "neutral",
                    "urgency": "normal",
                },
            )(),
            knowledge_context=result,
            shopify_context=None,
        )

        return await self.repo.create(
            user_id=user_id,
            conversation_id=conversation_id,
            action_type="reply",
            title="Draft AI reply",
            description="Draft a customer reply using knowledge base and support context.",
            payload={
                "body": composer_result["body"],
                "reply_type": composer_result.get("reply_type"),
                "requires_review": composer_result.get("requires_review"),
                "source_summary": composer_result.get("source_summary"),
                "knowledge_query": query,
                "knowledge_hits": hits,
                "sources": composer_result["sources"],
            },
            confidence=composer_result["confidence"],
            status="suggested",
            source="knowledge",
        )

    def _validate_shopify_execution_safety(self, action) -> None:
        payload = action.payload or {}
        prepared = payload.get("prepared_workflow")

        if not prepared:
            raise HTTPException(
                status_code=409,
                detail="Shopify action requires prepared_workflow before execution",
            )

        workflow = prepared.get("workflow") or {}
        decision = workflow.get("decision") or {}
        next_action = workflow.get("next_action")
        decision_status = decision.get("status")

        if next_action == "blocked" or decision_status == "blocked":
            raise HTTPException(
                status_code=409,
                detail=decision.get("message") or "Shopify action is blocked",
            )

        if (
            next_action == "request_more_information"
            or decision_status == "needs_information"
        ):
            raise HTTPException(
                status_code=409,
                detail=decision.get("message")
                or "Shopify action needs more information",
            )

        if next_action not in {
            "approval_required",
            "reply_ready",
            "manual_review",
        }:
            raise HTTPException(
                status_code=409,
                detail=f"Unsupported Shopify action next_action: {next_action}",
            )

    def _reply_quality_metadata(self, action) -> dict:
        payload = action.payload or {}
        source_summary = payload.get("source_summary") or {}
        sources = payload.get("sources") or {}

        return {
            "reply_type": payload.get("reply_type"),
            "requires_review": payload.get("requires_review"),
            "source_summary": source_summary,
            "intent": source_summary.get("intent") or sources.get("intent"),
            "sentiment": source_summary.get("sentiment") or sources.get("sentiment"),
            "urgency": source_summary.get("urgency") or sources.get("urgency"),
            "sources": sources,
        }

    @observe_suggested_action_execution
    async def _execute_action(self, user_id, action, payload: dict):
        if action.action_type == "assign":
            ticket = await TicketRepository(self.db).get_by_conversation(
                user_id=user_id,
                conversation_id=action.conversation_id,
            )

            if ticket is None:
                raise HTTPException(status_code=404, detail="Ticket not found")

            assigned_to = payload.get("assigned_to") or payload.get("assignee_id")

            if not assigned_to:
                raise HTTPException(
                    status_code=422,
                    detail="assigned_to is required for assign action",
                )

            await AssignmentService(
                self.db,
                user_id=user_id,
            ).assign(
                ticket_id=ticket.id,
                assigned_to=assigned_to,
            )

            return {
                "type": "assign",
                "ticket_id": str(ticket.id),
                "assigned_to": assigned_to,
            }

        if action.action_type == "apply_tag":
            tag_name = payload.get("tag") or payload.get("name")

            if not tag_name:
                raise HTTPException(
                    status_code=422,
                    detail="tag or name is required for apply_tag action",
                )

            tag = await ConversationTagService(self.db).add_tag(
                user_id=user_id,
                conversation_id=action.conversation_id,
                name=tag_name,
            )

            return {
                "type": "apply_tag",
                "tag": tag.name,
            }

        if action.action_type == "send_macro":
            macro_id = payload.get("macro_id")

            if not macro_id:
                raise HTTPException(
                    status_code=422,
                    detail="macro_id is required for send_macro action",
                )

            message = await MacroService(self.db).apply_to_conversation(
                user_id=user_id,
                actor_id=user_id,
                macro_id=macro_id,
                conversation_id=action.conversation_id,
            )

            return {
                "type": "send_macro",
                "message_id": str(message.id),
            }

        if action.action_type == "reply":
            body = payload.get("body")

            if not body:
                raise HTTPException(
                    status_code=422,
                    detail="body is required for reply action",
                )

            message = await InboxService(self.db).add_message(
                conversation_id=action.conversation_id,
                payload=ConversationMessageCreate(
                    sender_type=SenderType.AGENT,
                    body=body,
                    meta={
                        "source": "suggested_action",
                        "suggested_action_id": str(action.id),
                    },
                ),
            )

            draft_body = (action.payload or {}).get("body")
            if draft_body and draft_body == body:
                await ReplyQualityService(self.db).record_accept_without_edit(
                    user_id=user_id,
                    conversation_id=action.conversation_id,
                    reply_message_id=message.id,
                    draft_body=draft_body,
                    final_body=body,
                    reviewer_id=user_id,
                    metadata=self._reply_quality_metadata(action),
                )
            elif draft_body:
                await ReplyQualityService(self.db).record_accept_with_edit(
                    user_id=user_id,
                    conversation_id=action.conversation_id,
                    reply_message_id=message.id,
                    draft_body=draft_body,
                    final_body=body,
                    reviewer_id=user_id,
                    metadata=self._reply_quality_metadata(action),
                )

            return {
                "type": "reply",
                "message_id": str(message.id),
            }

        if action.action_type.startswith("shopify_"):
            self._validate_shopify_execution_safety(action)

            # Shopify actions now start a durable workflow from the system template.
            # A previously prepared workflow is useful context, but not required:
            # execution can safely rebuild the workflow from action_type + order_ref.
            order_ref = payload.get("order_ref") or (action.payload or {}).get(
                "order_ref"
            )
            if not order_ref:
                raise HTTPException(
                    status_code=422,
                    detail="order_ref is required for Shopify workflow action",
                )

            return await ShopifyActionWorkflowService(self.db).start_action_workflow(
                user_id=user_id,
                suggested_action=action,
                payload=payload,
            )

        if action.action_type == "close_ticket":
            ticket = await TicketRepository(self.db).get_by_conversation(
                user_id=user_id,
                conversation_id=action.conversation_id,
            )

            if ticket is None:
                raise HTTPException(status_code=404, detail="Ticket not found")

            updated = await TicketRepository(self.db).update(
                user_id=user_id,
                ticket_id=ticket.id,
                payload=TicketUpdate(status="closed"),
            )

            await SLAService(self.db).resolve_resolution_targets(
                ticket_id=ticket.id,
            )

            return {
                "type": "close_ticket",
                "ticket_id": str(updated.id),
                "status": updated.status,
            }

        if action.action_type == "escalate":
            ticket = await TicketRepository(self.db).get_by_conversation(
                user_id=user_id,
                conversation_id=action.conversation_id,
            )

            if ticket is None:
                raise HTTPException(status_code=404, detail="Ticket not found")

            updated = await TicketRepository(self.db).update(
                user_id=user_id,
                ticket_id=ticket.id,
                payload=TicketUpdate(
                    priority="urgent",
                    status="pending",
                ),
            )

            await ConversationTagService(self.db).add_tag(
                user_id=user_id,
                conversation_id=action.conversation_id,
                name="escalated",
            )

            return {
                "type": "escalate",
                "ticket_id": str(updated.id),
                "priority": updated.priority,
                "status": updated.status,
            }

        if action.action_type == "refund":
            raise HTTPException(
                status_code=501,
                detail="Refund execution requires Stripe/Shopify integration",
            )

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported suggested action type: {action.action_type}",
        )

    async def _get_action(self, user_id, action_id):
        action = await self.repo.get_for_user(
            user_id=user_id,
            action_id=action_id,
        )

        if action is None:
            raise HTTPException(status_code=404, detail="Suggested action not found")

        return action
