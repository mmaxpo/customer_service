from __future__ import annotations

from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceAgent, CustomerServiceAgentTimeOff


class AgentTimeOffService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, workspace_id, agent_id, actor_user_id, starts_at: datetime, ends_at: datetime, reason=None):
        if starts_at >= ends_at:
            raise HTTPException(status_code=422, detail="starts_at must be before ends_at")
        agent = await self.db.scalar(select(CustomerServiceAgent).where(
            CustomerServiceAgent.user_id == workspace_id, CustomerServiceAgent.id == agent_id
        ))
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        row = CustomerServiceAgentTimeOff(
            workspace_id=workspace_id, agent_id=agent_id,
            starts_at=_aware(starts_at), ends_at=_aware(ends_at),
            reason=reason, created_by_user_id=actor_user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list(self, *, workspace_id, agent_id=None):
        stmt = select(CustomerServiceAgentTimeOff).where(CustomerServiceAgentTimeOff.workspace_id == workspace_id)
        if agent_id is not None:
            stmt = stmt.where(CustomerServiceAgentTimeOff.agent_id == agent_id)
        return list((await self.db.scalars(stmt.order_by(CustomerServiceAgentTimeOff.starts_at))).all())

    async def delete(self, *, workspace_id, time_off_id):
        row = await self.db.scalar(select(CustomerServiceAgentTimeOff).where(
            CustomerServiceAgentTimeOff.workspace_id == workspace_id,
            CustomerServiceAgentTimeOff.id == time_off_id,
        ))
        if row is None:
            raise HTTPException(status_code=404, detail="Time-off entry not found")
        await self.db.delete(row)
        await self.db.commit()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
