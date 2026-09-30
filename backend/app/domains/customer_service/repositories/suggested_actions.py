from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceSuggestedAction


class SuggestedActionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs):
        obj = CustomerServiceSuggestedAction(**kwargs)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_for_user(self, user_id, action_id):
        result = await self.db.execute(
            select(CustomerServiceSuggestedAction).where(
                CustomerServiceSuggestedAction.user_id == user_id,
                CustomerServiceSuggestedAction.id == action_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_conversation(self, user_id, conversation_id):
        result = await self.db.execute(
            select(CustomerServiceSuggestedAction)
            .where(
                CustomerServiceSuggestedAction.user_id == user_id,
                CustomerServiceSuggestedAction.conversation_id == conversation_id,
                CustomerServiceSuggestedAction.status.in_(["suggested", "accepted"]),
            )
            .order_by(CustomerServiceSuggestedAction.created_at.desc())
        )
        return result.scalars().all()

    async def supersede_open_for_conversation(self, user_id, conversation_id):
        result = await self.db.execute(
            select(CustomerServiceSuggestedAction).where(
                CustomerServiceSuggestedAction.user_id == user_id,
                CustomerServiceSuggestedAction.conversation_id == conversation_id,
                CustomerServiceSuggestedAction.status.in_(["suggested", "accepted"]),
            )
        )

        actions = list(result.scalars().all())

        for action in actions:
            action.status = "superseded"

        await self.db.commit()
        return actions

    async def save(self, action):
        await self.db.commit()
        await self.db.refresh(action)
        return action
