from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Ticket,
    TicketAssignment,
    ConversationMessage,
    MessageSenderType,
)
from app.domains.customer_service.repositories.audit_logs import AuditLogRepository


class TicketAssignmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def active_assignment(self, ticket_id):
        result = await self.db.execute(
            select(TicketAssignment).where(
                TicketAssignment.ticket_id == ticket_id,
                TicketAssignment.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def assign(
        self, *, user_id, ticket_id, assigned_to, assigned_by, meta: dict | None = None
    ):
        lock_key = f"cs_ticket_assignment:{user_id}:{ticket_id}"
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )

        result = await self.db.execute(
            select(Ticket).where(Ticket.user_id == user_id, Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        if ticket is None:
            return None

        current = await self.active_assignment(ticket_id)
        if current and str(current.assigned_to) == str(assigned_to):
            return current

        if current:
            current.is_active = False

        assignment = TicketAssignment(
            user_id=user_id,
            ticket_id=ticket_id,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            is_active=True,
        )
        ticket.assigned_to = str(assigned_to) if assigned_to is not None else None
        self.db.add(assignment)
        assignment_meta = {
            "event": "ticket.assigned",
            "ticket_id": str(ticket_id),
            "assigned_to": str(assigned_to) if assigned_to else None,
        }
        if meta:
            assignment_meta.update(meta)
        self.db.add(
            ConversationMessage(
                conversation_id=ticket.conversation_id,
                sender_type=MessageSenderType.SYSTEM,
                body="Ticket assigned.",
                meta=assignment_meta,
            )
        )
        await AuditLogRepository(self.db).create(
            user_id=user_id,
            actor_id=assigned_by,
            entity_type="ticket",
            entity_id=ticket_id,
            action="ticket.assigned",
            message="Ticket assigned",
            meta=assignment_meta,
            commit=False,
        )
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment
