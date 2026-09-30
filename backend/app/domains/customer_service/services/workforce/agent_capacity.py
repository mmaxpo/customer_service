from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceAgent,
    Ticket,
)
from app.domains.customer_service.services.workforce.availability import AgentAvailabilityService


class AgentCapacityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.availability = AgentAvailabilityService(db)

    async def current_workload(
        self,
        *,
        user_id,
        agent_user_id,
    ) -> int:
        result = await self.db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == user_id,
                Ticket.assigned_to == str(agent_user_id),
                Ticket.status.in_(["open", "pending"]),
            )
        )

        return int(result.scalar() or 0)

    async def capacity_snapshot(
        self,
        *,
        user_id,
        agent: CustomerServiceAgent,
    ) -> dict:
        current = await self.current_workload(
            user_id=user_id,
            agent_user_id=agent.agent_user_id,
        )

        max_open = int(agent.max_open_tickets or 0)
        available_capacity = max(max_open - current, 0)

        availability = await self.availability.evaluate(agent=agent)
        can_accept = availability["routing_eligible"] and available_capacity > 0

        return {
            "agent_id": str(agent.id),
            "agent_user_id": str(agent.agent_user_id),
            "status": agent.status,
            "availability": agent.availability,
            **availability,
            "max_open_tickets": max_open,
            "current_open_tickets": current,
            "available_capacity": available_capacity,
            "can_accept_ticket": can_accept,
        }
