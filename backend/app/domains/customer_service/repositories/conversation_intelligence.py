from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    CustomerServiceConversationInsight,
)


class ConversationInsightRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_conversation_with_messages(self, user_id, conversation_id):
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )
        return result.scalars().unique().one_or_none()

    async def get_conversation_message_count(
        self, user_id, conversation_id
    ) -> int | None:
        conversation_exists = await self.db.scalar(
            select(Conversation.id).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )

        if conversation_exists is None:
            return None

        count = await self.db.scalar(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == conversation_id,
            )
        )

        return int(count or 0)

    async def get_latest(self, user_id, conversation_id):
        result = await self.db.execute(
            select(CustomerServiceConversationInsight)
            .where(
                CustomerServiceConversationInsight.user_id == user_id,
                CustomerServiceConversationInsight.conversation_id == conversation_id,
            )
            .order_by(CustomerServiceConversationInsight.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id,
        conversation_id,
        **values,
    ):
        existing = await self.get_latest(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if existing is not None:
            for key, value in values.items():
                setattr(existing, key, value)

            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        obj = CustomerServiceConversationInsight(
            user_id=user_id,
            conversation_id=conversation_id,
            **values,
        )

        self.db.add(obj)

        await self.db.commit()
        await self.db.refresh(obj)

        return obj

    async def list_for_conversation(self, user_id, conversation_id):
        result = await self.db.execute(
            select(CustomerServiceConversationInsight)
            .where(
                CustomerServiceConversationInsight.user_id == user_id,
                CustomerServiceConversationInsight.conversation_id == conversation_id,
            )
            .order_by(CustomerServiceConversationInsight.created_at.desc())
        )
        return result.scalars().all()
