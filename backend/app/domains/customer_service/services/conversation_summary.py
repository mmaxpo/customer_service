from __future__ import annotations

from fastapi import HTTPException

from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.services.ai_context_policy import (
    CustomerServiceAIContextPolicy,
)

from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)


class ConversationSummaryService:
    def __init__(self, db, policy: CustomerServiceAIContextPolicy | None = None):
        self.db = db
        self.policy = policy or CustomerServiceAIContextPolicy.from_env()
        self.conversation_repo = ConversationRepository(db)

    async def generate(self, *, user_id, conversation):
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        intelligence = await ConversationIntelligenceService(self.db).analyze(
            user_id=user_id,
            conversation_id=conversation.id,
            force_refresh=True,
        )

        messages = (
            await self.conversation_repo.list_recent_context_messages(
                user_id=user_id,
                conversation_id=conversation.id,
                limit=min(5, self.policy.recent_message_limit),
                include_internal_notes=self.policy.include_internal_notes,
            )
            or []
        )

        bodies = [
            message.body.strip()
            for message in messages
            if getattr(message, "body", None)
        ]

        summary = self.policy.trim_text("\n".join(bodies))

        return {
            "summary": summary,
            "intent": getattr(intelligence, "intent", None),
            "sentiment": getattr(intelligence, "sentiment", None),
            "urgency": getattr(intelligence, "urgency", None),
            "entities": getattr(intelligence, "entities", {}) or {},
        }
