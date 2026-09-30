from __future__ import annotations

from app.domains.customer_service.services.ai_reply_composer import (
    CustomerServiceAIReplyComposer,
)
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)
from app.domains.customer_service.services.knowledge import (
    CustomerServiceKnowledgeService,
)


class AIReplyRegenerationService:
    def __init__(self, db):
        self.db = db

    async def regenerate(
        self,
        *,
        user_id,
        conversation,
        customer_message: str,
        generation: int = 2,
    ):
        intelligence = await ConversationIntelligenceService(self.db).analyze(
            user_id=user_id,
            conversation_id=conversation.id,
            force_refresh=True,
        )

        knowledge = await CustomerServiceKnowledgeService(self.db).search_context(
            user_id=user_id,
            query=customer_message,
            k=3,
        )

        reply = CustomerServiceAIReplyComposer().compose(
            customer_message=customer_message,
            intelligence=intelligence,
            knowledge_context=knowledge,
            shopify_context=None,
        )

        return {
            "body": reply["body"],
            "confidence": reply["confidence"],
            "generation": generation,
            "regenerated": True,
            "sources": reply["sources"],
        }
