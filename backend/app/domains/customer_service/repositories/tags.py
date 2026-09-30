from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import ConversationTag


class ConversationTagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, *, user_id, conversation_id, name: str):
        normalized = name.strip().lower()

        existing = await self.db.execute(
            select(ConversationTag).where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id == conversation_id,
                ConversationTag.name == normalized,
            )
        )

        found = existing.scalar_one_or_none()
        if found:
            return found

        tag = ConversationTag(
            user_id=user_id,
            conversation_id=conversation_id,
            name=normalized,
        )

        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def list_for_conversation(self, *, user_id, conversation_id):
        result = await self.db.execute(
            select(ConversationTag)
            .where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id == conversation_id,
            )
            .order_by(ConversationTag.name.asc())
        )
        return result.scalars().all()

    async def remove(self, *, user_id, conversation_id, name: str):
        normalized = name.strip().lower()

        await self.db.execute(
            delete(ConversationTag).where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id == conversation_id,
                ConversationTag.name == normalized,
            )
        )

        await self.db.commit()
        return {"removed": normalized}
