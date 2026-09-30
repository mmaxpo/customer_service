from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    ConversationTag,
    Customer,
    Ticket,
)
from app.domains.customer_service.services.customer_activity import (
    CustomerActivityService,
)
from app.domains.customer_service.services.customers import CustomerService
from app.domains.customer_service.services.workflow_executions import (
    CustomerServiceWorkflowExecutionService,
)


class Customer360Service:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_360(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
        limit: int = 10,
    ) -> dict:
        customer = await self._get_customer(
            user_id=user_id,
            customer_id=customer_id,
        )

        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        summary = await CustomerService(self.db).get_customer_summary(
            user_id=user_id,
            customer_id=customer_id,
        )

        conversations = await self._recent_conversations(
            user_id=user_id,
            customer_id=customer_id,
            limit=limit,
        )
        conversation_ids = [conversation.id for conversation in conversations]

        tickets = await self._recent_tickets(
            user_id=user_id,
            conversation_ids=conversation_ids,
            limit=limit,
        )

        activity = await CustomerActivityService(self.db).list_activity(
            user_id=user_id,
            customer_id=customer_id,
            limit=limit,
        )

        workflow_executions = await CustomerServiceWorkflowExecutionService(
            self.db
        ).list(
            user_id=user_id,
            limit=200,
            offset=0,
        )

        workflow_executions = [
            execution
            for execution in workflow_executions
            if execution.get("customer_id") == str(customer_id)
        ][:limit]

        tags = await self._tags_for_conversations(
            user_id=user_id,
            conversation_ids=conversation_ids,
        )

        return {
            "customer": jsonable_encoder(customer),
            "summary": jsonable_encoder(summary),
            "recent_conversations": jsonable_encoder(conversations),
            "recent_tickets": jsonable_encoder(tickets),
            "recent_activity": jsonable_encoder(activity),
            "workflow_executions": jsonable_encoder(workflow_executions),
            "tags": sorted(tags),
        }

    async def _get_customer(self, *, user_id: UUID, customer_id: UUID):
        result = await self.db.execute(
            select(Customer).where(
                Customer.user_id == user_id,
                Customer.id == customer_id,
            )
        )
        return result.scalar_one_or_none()

    async def _recent_conversations(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
        limit: int,
    ):
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.customer_id == customer_id,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _recent_tickets(
        self,
        *,
        user_id: UUID,
        conversation_ids: list[UUID],
        limit: int,
    ):
        if not conversation_ids:
            return []

        result = await self.db.execute(
            select(Ticket)
            .where(
                Ticket.user_id == user_id,
                Ticket.conversation_id.in_(conversation_ids),
            )
            .order_by(Ticket.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _tags_for_conversations(
        self,
        *,
        user_id: UUID,
        conversation_ids: list[UUID],
    ) -> set[str]:
        if not conversation_ids:
            return set()

        result = await self.db.execute(
            select(ConversationTag).where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id.in_(conversation_ids),
            )
        )

        return {tag.name for tag in result.scalars().all() if tag.name}
