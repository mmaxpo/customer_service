from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceAgent
from app.domains.customer_service.repositories.teams import (
    CustomerServiceTeamRepository,
)
from app.domains.customer_service.services.workforce.agent_capacity import AgentCapacityService


class BestAgentSelector:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.capacity = AgentCapacityService(db)

    async def select_for_team(
        self,
        *,
        user_id,
        team_id,
        required_skills: list[str] | None = None,
        channel: str | None = None,
        language: str | None = None,
    ) -> CustomerServiceAgent | None:
        agents = await CustomerServiceTeamRepository(self.db).list_members(
            user_id=user_id,
            team_id=team_id,
        )

        candidates = []

        for agent in agents:
            snapshot = await self.capacity.capacity_snapshot(
                user_id=user_id,
                agent=agent,
            )

            if not snapshot["can_accept_ticket"]:
                continue

            if not self._matches_required_skills(
                agent,
                required_skills or [],
            ):
                continue

            if channel and channel not in (agent.channels or []):
                continue

            if language and language not in (agent.languages or []):
                continue

            candidates.append(
                {
                    "agent": agent,
                    "snapshot": snapshot,
                    "skill_score": self._skill_score(
                        agent,
                        required_skills or [],
                    ),
                }
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                -item["skill_score"],
                item["snapshot"]["current_open_tickets"],
                item["agent"].created_at,
            )
        )

        return candidates[0]["agent"]

    def _matches_required_skills(
        self,
        agent: CustomerServiceAgent,
        required_skills: list[str],
    ) -> bool:
        if not required_skills:
            return True

        agent_skills = set(agent.skills or [])
        return all(skill in agent_skills for skill in required_skills)

    def _skill_score(
        self,
        agent: CustomerServiceAgent,
        required_skills: list[str],
    ) -> int:
        agent_skills = set(agent.skills or [])
        return sum(1 for skill in required_skills if skill in agent_skills)
