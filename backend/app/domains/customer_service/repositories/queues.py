from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceQueue,
    CustomerServiceTeam,
)


class CustomerServiceQueueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: UUID,
        name: str,
        description: str | None = None,
        team_id: UUID | None = None,
        channel: str | None = None,
        intent: str | None = None,
        priority: str | None = None,
        priority_rank: int = 100,
        is_default: bool = False,
        is_active: bool = True,
        filters: dict | None = None,
        meta: dict | None = None,
    ) -> CustomerServiceQueue:
        queue = CustomerServiceQueue(
            user_id=user_id,
            name=name,
            description=description,
            team_id=team_id,
            channel=channel,
            intent=intent,
            priority=priority,
            priority_rank=priority_rank,
            is_default=is_default,
            is_active=is_active,
            filters=filters or {},
            meta=meta or {},
        )
        self.db.add(queue)
        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def list_for_user(
        self, *, user_id: UUID, active_only: bool | None = None, limit: int = 100
    ):
        stmt = select(CustomerServiceQueue).where(
            CustomerServiceQueue.user_id == user_id
        )

        if active_only is not None:
            stmt = stmt.where(CustomerServiceQueue.is_active.is_(active_only))

        result = await self.db.execute(
            stmt.order_by(
                CustomerServiceQueue.is_default.desc(),
                CustomerServiceQueue.priority_rank.asc(),
                CustomerServiceQueue.created_at.desc(),
            ).limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, *, user_id: UUID, queue_id: UUID):
        result = await self.db.execute(
            select(CustomerServiceQueue).where(
                CustomerServiceQueue.user_id == user_id,
                CustomerServiceQueue.id == queue_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, *, queue: CustomerServiceQueue, values: dict):
        for key, value in values.items():
            setattr(queue, key, value)

        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def delete(self, *, queue: CustomerServiceQueue):
        await self.db.delete(queue)
        await self.db.commit()

    async def team_belongs_to_user(self, *, user_id: UUID, team_id: UUID) -> bool:
        result = await self.db.execute(
            select(CustomerServiceTeam.id).where(
                CustomerServiceTeam.user_id == user_id,
                CustomerServiceTeam.id == team_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        queue_ids: list[str],
    ) -> list[CustomerServiceQueue]:
        if not queue_ids:
            return []

        result = await self.db.execute(
            select(CustomerServiceQueue).where(
                CustomerServiceQueue.user_id == user_id,
                CustomerServiceQueue.id.in_(queue_ids),
                CustomerServiceQueue.is_active.is_(True),
            )
        )
        return list(result.scalars().all())
