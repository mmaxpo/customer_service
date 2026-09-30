from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    ConversationTag,
    Customer,
    SLAViolation,
    Ticket,
    TicketStatus,
)
from app.models.models import PlatformJob


class CustomerServiceDashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def aggregates(self, *, user_id) -> dict:
        open_tickets = await self.db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == user_id,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.PENDING]),
            )
        )

        unassigned_tickets = await self.db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.user_id == user_id,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.PENDING]),
                Ticket.assigned_to.is_(None),
            )
        )

        sla_at_risk = await self.db.scalar(
            select(func.count(SLAViolation.id)).where(
                SLAViolation.user_id == user_id,
                SLAViolation.status == "open",
            )
        )

        refund_conversations = await self.db.scalar(
            select(func.count(func.distinct(ConversationTag.conversation_id))).where(
                ConversationTag.user_id == user_id,
                ConversationTag.name == "refund",
            )
        )

        workflow_runs = await self.db.scalar(
            select(func.count(PlatformJob.id)).where(
                PlatformJob.user_id == user_id,
                PlatformJob.job_type == "workflow.run",
            )
        )

        customers = await self.db.scalar(
            select(func.count(Customer.id)).where(Customer.user_id == user_id)
        )

        return {
            "open_tickets": open_tickets or 0,
            "unassigned_tickets": unassigned_tickets or 0,
            "sla_at_risk": sla_at_risk or 0,
            "refund_conversations": refund_conversations or 0,
            "workflow_runs": workflow_runs or 0,
            "customers": customers or 0,
        }
