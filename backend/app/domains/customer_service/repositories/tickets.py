from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import Ticket
from app.domains.customer_service.schemas.tickets import TicketCreate, TicketUpdate


class TicketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id, ticket: TicketCreate, *, workspace_id=None):
        obj = Ticket(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=ticket.conversation_id,
            title=ticket.title,
            status=ticket.status,
            priority=ticket.priority,
            assigned_to=ticket.assigned_to,
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def list(self, user_id):
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
        )
        return result.scalars().all()

    async def get(self, user_id, ticket_id: UUID):
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.user_id == user_id,
                Ticket.id == ticket_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, user_id, ticket_id: UUID, payload: TicketUpdate):
        ticket = await self.get(user_id, ticket_id)

        if ticket is None:
            return None

        data = payload.model_dump(exclude_unset=True)

        for key, value in data.items():
            setattr(ticket, key, value)

        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def get_by_conversation(self, user_id, conversation_id):
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.user_id == user_id,
                Ticket.conversation_id == conversation_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_conversation_id(self, conversation_id):
        result = await self.db.execute(
            select(Ticket).where(Ticket.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()
