from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.agents import (
    CustomerServiceAgentRepository,
)
from app.domains.customer_service.schemas.agents import (
    AgentCreate,
    AgentUpdate,
)
from datetime import datetime, timezone


class CustomerServiceAgentService:
    def __init__(self, db: AsyncSession):
        self.repo = CustomerServiceAgentRepository(db)

    async def create(self, *, user_id, payload: AgentCreate):
        return await self.repo.create(
            user_id=user_id,
            agent_user_id=payload.agent_user_id,
            display_name=payload.display_name,
            email=payload.email,
            status=payload.status,
            availability=payload.availability,
            availability_mode=payload.availability_mode,
            schedule_timezone=payload.schedule_timezone,
            weekly_schedule=payload.weekly_schedule,
            skills=payload.skills,
            channels=payload.channels,
            languages=payload.languages,
            max_open_tickets=payload.max_open_tickets,
            meta=payload.meta,
        )

    async def list_for_user(
        self,
        *,
        user_id,
        active_only: bool | None = None,
        available_only: bool | None = None,
    ):
        return await self.repo.list_for_user(
            user_id=user_id,
            active_only=active_only,
            available_only=available_only,
        )

    async def get(self, *, user_id, agent_id):
        agent = await self.repo.get(
            user_id=user_id,
            agent_id=agent_id,
        )
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    async def update(self, *, user_id, agent_id, payload: AgentUpdate):
        agent = await self.get(
            user_id=user_id,
            agent_id=agent_id,
        )
        return await self.repo.update(
            agent=agent,
            values=payload.model_dump(exclude_unset=True),
        )

    async def delete(self, *, user_id, agent_id):
        agent = await self.get(
            user_id=user_id,
            agent_id=agent_id,
        )
        await self.repo.delete(agent=agent)
        return None

    async def set_presence(self, *, workspace_id, agent_user_id, status: str):
        agent = await self.repo.get_by_agent_user_id(
            user_id=workspace_id, agent_user_id=agent_user_id
        )
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent profile not found")
        agent.availability = status
        agent.availability_source = "manual"
        now = datetime.now(timezone.utc)
        agent.last_presence_at = now
        agent.last_activity_at = now
        await self.repo.db.commit()
        await self.repo.db.refresh(agent)
        return agent

    async def record_activity(self, *, workspace_id, agent_user_id):
        agent = await self.repo.get_by_agent_user_id(user_id=workspace_id, agent_user_id=agent_user_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent profile not found")
        now = datetime.now(timezone.utc)
        if agent.availability == "away" and getattr(agent, "availability_source", "manual") == "idle":
            agent.availability = "available"
            agent.availability_source = "manual"
        agent.last_presence_at = now
        agent.last_activity_at = now
        await self.repo.db.commit()
        await self.repo.db.refresh(agent)
        return agent
