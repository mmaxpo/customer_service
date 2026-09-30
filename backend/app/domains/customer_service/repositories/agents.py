from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceAgent


class CustomerServiceAgentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: UUID,
        agent_user_id: UUID,
        display_name: str,
        email: str | None = None,
        status: str = "active",
        availability: str = "available",
        availability_mode: str = "manual",
        schedule_timezone: str | None = None,
        weekly_schedule: dict | None = None,
        skills: list | None = None,
        channels: list | None = None,
        languages: list | None = None,
        max_open_tickets: int = 20,
        meta: dict | None = None,
    ) -> CustomerServiceAgent:
        existing = await self.get_by_agent_user_id(
            user_id=user_id,
            agent_user_id=agent_user_id,
        )
        if existing is not None:
            return existing

        agent = CustomerServiceAgent(
            user_id=user_id,
            agent_user_id=agent_user_id,
            display_name=display_name,
            email=email,
            status=status,
            availability=availability,
            availability_mode=availability_mode,
            schedule_timezone=schedule_timezone,
            weekly_schedule=weekly_schedule,
            skills=skills or [],
            channels=channels or [],
            languages=languages or [],
            max_open_tickets=max_open_tickets,
            meta=meta or {},
        )

        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        active_only: bool | None = None,
        available_only: bool | None = None,
        limit: int = 100,
    ) -> list[CustomerServiceAgent]:
        stmt = select(CustomerServiceAgent).where(
            CustomerServiceAgent.user_id == user_id,
        )

        if active_only is True:
            stmt = stmt.where(CustomerServiceAgent.status == "active")

        if available_only is True:
            stmt = stmt.where(CustomerServiceAgent.availability == "available")

        result = await self.db.execute(
            stmt.order_by(CustomerServiceAgent.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get(
        self,
        *,
        user_id: UUID,
        agent_id: UUID,
    ) -> CustomerServiceAgent | None:
        result = await self.db.execute(
            select(CustomerServiceAgent).where(
                CustomerServiceAgent.user_id == user_id,
                CustomerServiceAgent.id == agent_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_agent_user_id(
        self,
        *,
        user_id: UUID,
        agent_user_id: UUID,
    ) -> CustomerServiceAgent | None:
        result = await self.db.execute(
            select(CustomerServiceAgent).where(
                CustomerServiceAgent.user_id == user_id,
                CustomerServiceAgent.agent_user_id == agent_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_agent_user_ids(
        self,
        *,
        user_id: UUID,
        agent_user_ids: list[str],
    ) -> list[CustomerServiceAgent]:
        if not agent_user_ids:
            return []

        result = await self.db.execute(
            select(CustomerServiceAgent).where(
                CustomerServiceAgent.user_id == user_id,
                CustomerServiceAgent.agent_user_id.in_(agent_user_ids),
            )
        )
        return list(result.scalars().all())

    async def update(
        self,
        *,
        agent: CustomerServiceAgent,
        values: dict,
    ) -> CustomerServiceAgent:
        for key, value in values.items():
            setattr(agent, key, value)

        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def delete(
        self,
        *,
        agent: CustomerServiceAgent,
    ) -> None:
        await self.db.delete(agent)
        await self.db.commit()

    async def list_matching_profiles(
        self,
        *,
        user_id: UUID,
        channels: list[str] | None = None,
        skills: list[str] | None = None,
        languages: list[str] | None = None,
        available_only: bool = True,
        active_only: bool = True,
    ) -> list[CustomerServiceAgent]:
        agents = await self.list_for_user(
            user_id=user_id,
            active_only=active_only,
            available_only=available_only,
            limit=500,
        )

        channels = channels or []
        skills = skills or []
        languages = languages or []

        def has_all(values: list, required: list[str]) -> bool:
            current = {str(item).lower() for item in values or []}
            return all(str(item).lower() in current for item in required)

        matched = []

        for agent in agents:
            if channels and not has_all(agent.channels or [], channels):
                continue

            if skills and not has_all(agent.skills or [], skills):
                continue

            if languages and not has_all(agent.languages or [], languages):
                continue

            matched.append(agent)

        return matched
