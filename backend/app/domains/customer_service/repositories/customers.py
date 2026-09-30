from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import Customer, Conversation, Ticket


class CustomerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, customer: Customer) -> Customer:
        if customer.email:
            normalized_email = str(customer.email).strip().lower()
            customer.email = normalized_email

            ownership_key = customer.workspace_id or customer.user_id
            lock_key = f"cs_customer_identity:{ownership_key}:{normalized_email}"

            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

            ownership_filter = (
                Customer.workspace_id == customer.workspace_id
                if customer.workspace_id is not None
                else Customer.user_id == customer.user_id
            )
            existing = await self.db.scalar(
                select(Customer.id).where(
                    ownership_filter,
                    func.lower(Customer.email) == normalized_email,
                )
            )

            if existing is not None:
                raise ValueError("customer with this email already exists")

        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        return customer

    async def list(self, user_id):
        result = await self.db.execute(
            select(Customer)
            .where(Customer.user_id == user_id)
            .order_by(Customer.created_at.desc())
        )
        return result.scalars().all()

    async def get(self, *, user_id, customer_id):
        result = await self.db.execute(
            select(Customer).where(
                Customer.user_id == user_id,
                Customer.id == customer_id,
            )
        )
        return result.scalar_one_or_none()

    async def summary(self, *, user_id, customer_id):
        customer = await self.get(user_id=user_id, customer_id=customer_id)
        if customer is None:
            return None

        conversations_result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.customer_id == customer_id,
            )
            .order_by(Conversation.updated_at.desc())
        )
        conversations = list(conversations_result.scalars().all())
        conversation_ids = [conversation.id for conversation in conversations]

        tickets = []
        if conversation_ids:
            tickets_result = await self.db.execute(
                select(Ticket)
                .where(
                    Ticket.user_id == user_id,
                    Ticket.conversation_id.in_(conversation_ids),
                )
                .order_by(Ticket.updated_at.desc())
            )
            tickets = list(tickets_result.scalars().all())

        open_statuses = {"open", "pending"}
        closed_statuses = {"resolved", "closed"}

        return {
            "customer_id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "conversation_count": len(conversations),
            "ticket_count": len(tickets),
            "open_ticket_count": sum(
                1
                for ticket in tickets
                if getattr(ticket.status, "value", str(ticket.status)) in open_statuses
            ),
            "closed_ticket_count": sum(
                1
                for ticket in tickets
                if getattr(ticket.status, "value", str(ticket.status))
                in closed_statuses
            ),
            "channels": sorted(
                {
                    conversation.channel
                    for conversation in conversations
                    if conversation.channel
                }
            ),
            "first_seen_at": min(
                [conversation.created_at for conversation in conversations],
                default=customer.created_at,
            ),
            "last_seen_at": max(
                [conversation.updated_at for conversation in conversations],
                default=customer.updated_at,
            ),
            "latest_conversation_id": conversations[0].id if conversations else None,
            "latest_ticket_id": tickets[0].id if tickets else None,
        }
