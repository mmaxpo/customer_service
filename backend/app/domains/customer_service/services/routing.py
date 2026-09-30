from __future__ import annotations

from collections import Counter

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.analytics import AnalyticsRepository
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.routing import (
    AutoAssignDecision,
    AutoAssignRequest,
    AutoAssignResult,
)
from app.domains.customer_service.services.assignment import AssignmentService


class CustomerServiceRoutingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ticket_repo = TicketRepository(db)
        self.analytics_repo = AnalyticsRepository(db)

    async def auto_assign_ticket(
        self,
        *,
        user_id,
        ticket_id,
        payload: AutoAssignRequest,
    ) -> AutoAssignResult:
        ticket = await self.ticket_repo.get(user_id, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")

        decision = await self.decide_assignee(
            user_id=user_id,
            ticket_id=ticket_id,
            payload=payload,
        )

        assignment = await AssignmentService(
            db=self.db,
            user_id=user_id,
        ).assign(
            ticket_id=ticket_id,
            assigned_to=decision.assigned_to,
        )

        if assignment is None:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return AutoAssignResult(
            decision=decision,
            assignment_id=assignment.id,
        )

    async def decide_assignee(
        self,
        *,
        user_id,
        ticket_id,
        payload: AutoAssignRequest,
    ) -> AutoAssignDecision:
        candidate_ids = [str(item) for item in payload.candidate_assignee_ids]

        workload_rows = await self.analytics_repo.workload_by_assignee(user_id)
        load_by_assignee = Counter(
            {
                str(row["assigned_to"]): int(row["open_or_pending_tickets"])
                for row in workload_rows
            }
        )

        candidate_loads = {
            candidate_id: load_by_assignee.get(candidate_id, 0)
            for candidate_id in candidate_ids
        }

        if payload.strategy == "first_available":
            selected = candidate_ids[0]
        else:
            selected = min(
                candidate_ids,
                key=lambda candidate_id: (
                    candidate_loads[candidate_id],
                    candidate_id,
                ),
            )

        reason = payload.reason or (
            f"Auto-assigned using {payload.strategy}; selected lowest workload candidate."
        )

        return AutoAssignDecision(
            ticket_id=ticket_id,
            assigned_to=selected,
            strategy=payload.strategy,
            reason=reason,
            candidate_loads=candidate_loads,
        )
