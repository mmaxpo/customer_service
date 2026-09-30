from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.queues import (
    CustomerServiceQueueRepository,
)
from app.domains.customer_service.schemas.queues import QueueCreate, QueueUpdate


class CustomerServiceQueueService:
    def __init__(self, db: AsyncSession):
        self.repo = CustomerServiceQueueRepository(db)

    async def create(self, *, user_id, payload: QueueCreate):
        await self._validate_team(user_id=user_id, team_id=payload.team_id)

        return await self.repo.create(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            team_id=payload.team_id,
            channel=payload.channel,
            intent=payload.intent,
            priority=payload.priority,
            priority_rank=payload.priority_rank,
            is_default=payload.is_default,
            is_active=payload.is_active,
            filters=payload.filters,
            meta=payload.meta,
        )

    async def list_for_user(self, *, user_id, active_only: bool | None = None):
        return await self.repo.list_for_user(user_id=user_id, active_only=active_only)

    async def get(self, *, user_id, queue_id):
        queue = await self.repo.get(user_id=user_id, queue_id=queue_id)
        if queue is None:
            raise HTTPException(status_code=404, detail="Queue not found")
        return queue

    async def update(self, *, user_id, queue_id, payload: QueueUpdate):
        queue = await self.get(user_id=user_id, queue_id=queue_id)
        values = payload.model_dump(exclude_unset=True)

        if "team_id" in values:
            await self._validate_team(user_id=user_id, team_id=values["team_id"])

        return await self.repo.update(queue=queue, values=values)

    async def delete(self, *, user_id, queue_id):
        queue = await self.get(user_id=user_id, queue_id=queue_id)
        await self.repo.delete(queue=queue)

    async def _validate_team(self, *, user_id, team_id):
        if team_id is None:
            return

        exists = await self.repo.team_belongs_to_user(user_id=user_id, team_id=team_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Team not found")
