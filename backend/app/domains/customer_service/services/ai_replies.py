from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.services.ai_reply_composer import (
    CustomerServiceAIReplyComposer,
)
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)
from app.domains.customer_service.services.knowledge import (
    CustomerServiceKnowledgeService,
)


class AIReplyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compose_for_conversation(
        self,
        *,
        user_id,
        conversation_id,
        customer_message: str | None = None,
        shopify_context: dict | None = None,
        force_refresh_intelligence: bool = False,
    ) -> dict:
        intelligence = await ConversationIntelligenceService(self.db).analyze(
            user_id=user_id,
            conversation_id=conversation_id,
            force_refresh=force_refresh_intelligence,
        )

        if intelligence is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        message = customer_message or await self._latest_customer_message(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        knowledge = await CustomerServiceKnowledgeService(self.db).search_context(
            user_id=user_id,
            query=message or intelligence.summary,
            k=3,
        )

        return CustomerServiceAIReplyComposer().compose(
            customer_message=message or intelligence.summary,
            intelligence=intelligence,
            knowledge_context=knowledge,
            shopify_context=shopify_context,
        )

    async def _latest_customer_message(self, *, user_id, conversation_id) -> str | None:
        message = await ConversationRepository(
            self.db,
        ).get_latest_customer_message(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        return message.body if message is not None else None
