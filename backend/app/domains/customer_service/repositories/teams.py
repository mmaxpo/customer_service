from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceAgent,
    CustomerServiceTeam,
    CustomerServiceTeamMember,
)


class CustomerServiceTeamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        user_id: UUID,
        name: str,
        description: str | None = None,
        is_active: bool = True,
        meta: dict | None = None,
    ) -> CustomerServiceTeam:
        team = CustomerServiceTeam(
            user_id=user_id,
            name=name,
            description=description,
            is_active=is_active,
            meta=meta or {},
        )
        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        active_only: bool | None = None,
        limit: int = 100,
    ) -> list[CustomerServiceTeam]:
        stmt = select(CustomerServiceTeam).where(
            CustomerServiceTeam.user_id == user_id,
        )

        if active_only is not None:
            stmt = stmt.where(CustomerServiceTeam.is_active.is_(active_only))

        result = await self.db.execute(
            stmt.order_by(CustomerServiceTeam.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get(
        self,
        *,
        user_id: UUID,
        team_id: UUID,
    ) -> CustomerServiceTeam | None:
        result = await self.db.execute(
            select(CustomerServiceTeam).where(
                CustomerServiceTeam.user_id == user_id,
                CustomerServiceTeam.id == team_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        team: CustomerServiceTeam,
        values: dict,
    ) -> CustomerServiceTeam:
        for key, value in values.items():
            setattr(team, key, value)

        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def delete(
        self,
        *,
        team: CustomerServiceTeam,
    ) -> None:
        await self.db.delete(team)
        await self.db.commit()

    async def add_member(
        self,
        *,
        user_id: UUID,
        team_id: UUID,
        agent_id: UUID,
    ) -> CustomerServiceTeamMember | None:
        agent = await self.db.get(CustomerServiceAgent, agent_id)
        if agent is None or agent.user_id != user_id:
            return None

        existing = await self.get_member(
            user_id=user_id,
            team_id=team_id,
            agent_id=agent_id,
        )
        if existing is not None:
            return existing

        member = CustomerServiceTeamMember(
            user_id=user_id,
            team_id=team_id,
            agent_id=agent_id,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def get_member(
        self,
        *,
        user_id: UUID,
        team_id: UUID,
        agent_id: UUID,
    ) -> CustomerServiceTeamMember | None:
        result = await self.db.execute(
            select(CustomerServiceTeamMember).where(
                CustomerServiceTeamMember.user_id == user_id,
                CustomerServiceTeamMember.team_id == team_id,
                CustomerServiceTeamMember.agent_id == agent_id,
            )
        )
        return result.scalar_one_or_none()

    async def remove_member(
        self,
        *,
        member: CustomerServiceTeamMember,
    ) -> None:
        await self.db.delete(member)
        await self.db.commit()

    async def list_members(
        self,
        *,
        user_id: UUID,
        team_id: UUID,
    ) -> list[CustomerServiceAgent]:
        result = await self.db.execute(
            select(CustomerServiceAgent)
            .join(
                CustomerServiceTeamMember,
                CustomerServiceTeamMember.agent_id == CustomerServiceAgent.id,
            )
            .where(
                CustomerServiceTeamMember.user_id == user_id,
                CustomerServiceTeamMember.team_id == team_id,
            )
            .order_by(CustomerServiceAgent.display_name.asc())
        )
        return list(result.scalars().all())

    async def list_agents_for_teams(
        self,
        *,
        user_id: UUID,
        team_ids: list[str],
        active_only: bool = True,
        available_only: bool = True,
    ) -> list[CustomerServiceAgent]:
        if not team_ids:
            return []

        stmt = (
            select(CustomerServiceAgent)
            .join(
                CustomerServiceTeamMember,
                CustomerServiceTeamMember.agent_id == CustomerServiceAgent.id,
            )
            .join(
                CustomerServiceTeam,
                CustomerServiceTeam.id == CustomerServiceTeamMember.team_id,
            )
            .where(
                CustomerServiceTeamMember.user_id == user_id,
                CustomerServiceTeamMember.team_id.in_(team_ids),
                CustomerServiceTeam.user_id == user_id,
                CustomerServiceTeam.is_active.is_(True),
                CustomerServiceAgent.user_id == user_id,
            )
            .order_by(CustomerServiceAgent.display_name.asc())
        )

        if active_only:
            stmt = stmt.where(CustomerServiceAgent.status == "active")

        if available_only:
            stmt = stmt.where(CustomerServiceAgent.availability == "available")

        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_agent_user_ids_for_teams(
        self,
        *,
        user_id: UUID,
        team_ids: list[str],
    ) -> list[str]:
        if not team_ids:
            return []

        result = await self.db.execute(
            select(CustomerServiceAgent.agent_user_id)
            .join(
                CustomerServiceTeamMember,
                CustomerServiceTeamMember.agent_id == CustomerServiceAgent.id,
            )
            .where(
                CustomerServiceTeamMember.user_id == user_id,
                CustomerServiceTeamMember.team_id.in_(team_ids),
                CustomerServiceAgent.status == "active",
                CustomerServiceAgent.availability == "available",
            )
            .order_by(CustomerServiceAgent.display_name.asc())
        )

        return [str(row[0]) for row in result.all()]
