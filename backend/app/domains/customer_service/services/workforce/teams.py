from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.teams import (
    CustomerServiceTeamRepository,
)
from app.domains.customer_service.schemas.teams import (
    TeamCreate,
    TeamUpdate,
)


class CustomerServiceTeamService:
    def __init__(self, db: AsyncSession):
        self.repo = CustomerServiceTeamRepository(db)

    async def create(self, *, user_id, payload: TeamCreate):
        return await self.repo.create(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            meta=payload.meta,
        )

    async def list_for_user(self, *, user_id, active_only: bool | None = None):
        return await self.repo.list_for_user(
            user_id=user_id,
            active_only=active_only,
        )

    async def get(self, *, user_id, team_id):
        team = await self.repo.get(user_id=user_id, team_id=team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")
        return team

    async def get_detail(self, *, user_id, team_id):
        team = await self.get(user_id=user_id, team_id=team_id)
        members = await self.repo.list_members(user_id=user_id, team_id=team_id)

        data = {
            "id": team.id,
            "user_id": team.user_id,
            "name": team.name,
            "description": team.description,
            "is_active": team.is_active,
            "meta": team.meta,
            "created_at": team.created_at,
            "updated_at": team.updated_at,
            "members": members,
        }
        return data

    async def update(self, *, user_id, team_id, payload: TeamUpdate):
        team = await self.get(user_id=user_id, team_id=team_id)
        return await self.repo.update(
            team=team,
            values=payload.model_dump(exclude_unset=True),
        )

    async def delete(self, *, user_id, team_id):
        team = await self.get(user_id=user_id, team_id=team_id)
        await self.repo.delete(team=team)
        return None

    async def add_member(self, *, user_id, team_id, agent_id):
        await self.get(user_id=user_id, team_id=team_id)

        member = await self.repo.add_member(
            user_id=user_id,
            team_id=team_id,
            agent_id=agent_id,
        )

        if member is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        return member

    async def remove_member(self, *, user_id, team_id, agent_id):
        await self.get(user_id=user_id, team_id=team_id)

        member = await self.repo.get_member(
            user_id=user_id,
            team_id=team_id,
            agent_id=agent_id,
        )

        if member is None:
            raise HTTPException(status_code=404, detail="Team member not found")

        await self.repo.remove_member(member=member)
        return None
