from fastapi import HTTPException

from app.domains.customer_service.repositories.audit_logs import AuditLogRepository
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.services.tags import ConversationTagService
from app.domains.customer_service.services.shopify_context import (
    ShopifyOrderContextResolver,
)
from app.domains.customer_service.services.suggested_actions import (
    SuggestedActionService,
)
from app.domains.customer_service.schemas.triage import TriageResult, TriagePriority


class AutoTriageService:
    def __init__(self, db=None):
        self.db = db
        self.tag_service = ConversationTagService(db) if db is not None else None

    async def classify(self, message: str):
        lower = message.lower()
        tags = []
        intent = "general"
        priority = TriagePriority.NORMAL
        sentiment = "neutral"

        if "refund" in lower:
            tags.append("refund")
            intent = "refund_request"
            sentiment = "negative"

        if (
            "where is my order" in lower
            or "tracking" in lower
            or "shipping" in lower
            or "package" in lower
        ):
            tags.append("shipping")
            intent = "shipping_status"
        if "broken" in lower or "damaged" in lower:
            tags.append("damaged_item")
            sentiment = "negative"
        if "urgent" in lower or "asap" in lower:
            tags.append("urgent")
            priority = TriagePriority.HIGH
        if "angry" in lower or "terrible" in lower or "worst" in lower:
            sentiment = "negative"
            priority = TriagePriority.HIGH
        return TriageResult(
            intent=intent,
            sentiment=sentiment,
            priority=priority,
            confidence=0.90,
            tags=list(dict.fromkeys(tags)),
        )

    async def classify_and_apply(
        self, *, user_id, conversation_id, message: str, actor_id=None
    ):
        if self.db is not None:
            conversation = await ConversationRepository(self.db).get_for_user(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            if conversation is None:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found",
                )

        result = await self.classify(message)

        if self.tag_service is not None:
            for tag in result.tags:
                await self.tag_service.add_tag(
                    user_id=user_id, conversation_id=conversation_id, name=tag
                )

        if self.db is not None:
            ticket = await TicketRepository(self.db).get_by_conversation(
                user_id, conversation_id
            )
            if ticket is not None and result.priority.value != ticket.priority:
                ticket.priority = result.priority.value

            shopify_context = await ShopifyOrderContextResolver(self.db).resolve(
                user_id=user_id,
                message=message,
            )

            await SuggestedActionService(self.db).suggest_shopify_actions(
                user_id=user_id,
                conversation_id=conversation_id,
                triage_result=result,
                shopify_context=shopify_context,
            )

            await AuditLogRepository(self.db).create(
                user_id=user_id,
                actor_id=actor_id,
                entity_type="conversation",
                entity_id=conversation_id,
                action="conversation.triaged",
                message="Conversation auto-triaged",
                meta={
                    **result.model_dump(mode="json"),
                    "shopify_context": shopify_context,
                },
            )
        return result
