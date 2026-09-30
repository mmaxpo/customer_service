from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    Customer,
    CustomerServiceAuditLog,
    Ticket,
)
from app.domains.customer_service.services.workflow_executions import (
    CustomerServiceWorkflowExecutionService,
)


class CustomerActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _source_limit(self, limit: int) -> int:
        # Bound each activity source before merging. A customer can have many
        # conversations/messages/audit logs; never load the full history just
        # to return a small activity feed page.
        return max(1, min(limit, 500))

    async def list_activity(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
        limit: int = 100,
    ) -> list[dict]:
        customer = await self._get_customer(user_id=user_id, customer_id=customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        events: list[dict] = []
        source_limit = self._source_limit(limit)

        events.append(
            self._event(
                type="customer.created",
                timestamp=customer.created_at,
                title="Customer created",
                description=customer.email or customer.name,
                entity_id=customer.id,
                entity_type="customer",
                metadata={
                    "name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone,
                    "status": self._value(customer.status),
                },
            )
        )

        conversations = await self._list_conversations(
            user_id=user_id,
            customer_id=customer_id,
            limit=source_limit,
        )
        conversation_ids = [conversation.id for conversation in conversations]

        for conversation in conversations:
            events.append(
                self._event(
                    type="conversation.created",
                    timestamp=conversation.created_at,
                    title="Conversation created",
                    description=conversation.subject,
                    entity_id=conversation.id,
                    entity_type="conversation",
                    metadata={
                        "channel": conversation.channel,
                        "status": self._value(conversation.status),
                    },
                )
            )

        events.extend(
            await self._message_events(
                user_id=user_id,
                conversation_ids=conversation_ids,
                limit=source_limit,
            )
        )
        events.extend(
            await self._ticket_events(
                user_id=user_id,
                conversation_ids=conversation_ids,
                limit=source_limit,
            )
        )
        events.extend(
            await self._audit_events(
                user_id=user_id,
                customer_id=customer_id,
                conversation_ids=conversation_ids,
                limit=source_limit,
            )
        )
        events.extend(
            await self._workflow_events(
                user_id=user_id,
                customer_id=customer_id,
                limit=source_limit,
            )
        )

        events.sort(key=lambda event: event["timestamp"], reverse=True)
        return events[:limit]

    async def _get_customer(self, *, user_id: UUID, customer_id: UUID):
        result = await self.db.execute(
            select(Customer).where(
                Customer.user_id == user_id,
                Customer.id == customer_id,
            )
        )
        return result.scalar_one_or_none()

    async def _list_conversations(
        self, *, user_id: UUID, customer_id: UUID, limit: int
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

    async def _message_events(
        self,
        *,
        user_id: UUID,
        conversation_ids: list[UUID],
        limit: int,
    ) -> list[dict]:
        if not conversation_ids:
            return []

        result = await self.db.execute(
            select(ConversationMessage)
            .join(Conversation, ConversationMessage.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == user_id,
                ConversationMessage.conversation_id.in_(conversation_ids),
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )

        events = []
        for message in result.scalars().all():
            sender_type = self._value(message.sender_type)
            events.append(
                self._event(
                    type=(
                        "internal_note.created"
                        if sender_type == "internal_note"
                        else "message.created"
                    ),
                    timestamp=message.created_at,
                    title=(
                        "Internal note"
                        if sender_type == "internal_note"
                        else f"{sender_type.title()} message"
                    ),
                    description=message.body,
                    entity_id=message.id,
                    entity_type="conversation_message",
                    metadata={
                        "conversation_id": str(message.conversation_id),
                        "sender_type": sender_type,
                        "meta": message.meta,
                    },
                )
            )

        return events

    async def _ticket_events(
        self,
        *,
        user_id: UUID,
        conversation_ids: list[UUID],
        limit: int,
    ) -> list[dict]:
        if not conversation_ids:
            return []

        result = await self.db.execute(
            select(Ticket)
            .where(
                Ticket.user_id == user_id,
                Ticket.conversation_id.in_(conversation_ids),
            )
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )

        events = []
        for ticket in result.scalars().all():
            events.append(
                self._event(
                    type="ticket.created",
                    timestamp=ticket.created_at,
                    title="Ticket created",
                    description=ticket.title,
                    entity_id=ticket.id,
                    entity_type="ticket",
                    metadata={
                        "conversation_id": str(ticket.conversation_id),
                        "status": self._value(ticket.status),
                        "priority": self._value(ticket.priority),
                        "assigned_to": ticket.assigned_to,
                    },
                )
            )

        return events

    async def _audit_events(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
        conversation_ids: list[UUID],
        limit: int,
    ) -> list[dict]:
        entity_ids = [customer_id, *conversation_ids]

        result = await self.db.execute(
            select(CustomerServiceAuditLog)
            .where(
                CustomerServiceAuditLog.user_id == user_id,
                CustomerServiceAuditLog.entity_id.in_(entity_ids),
            )
            .order_by(CustomerServiceAuditLog.created_at.desc())
            .limit(limit)
        )

        return [
            self._event(
                type=f"audit.{log.action}",
                timestamp=log.created_at,
                title=log.action,
                description=log.message,
                entity_id=log.id,
                entity_type="audit_log",
                metadata={
                    "actor_id": str(log.actor_id) if log.actor_id else None,
                    "audit_entity_type": log.entity_type,
                    "audit_entity_id": str(log.entity_id) if log.entity_id else None,
                    "meta": log.meta,
                },
            )
            for log in result.scalars().all()
        ]

    async def _workflow_events(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
        limit: int,
    ) -> list[dict]:
        executions = await CustomerServiceWorkflowExecutionService(self.db).list(
            user_id=user_id,
            limit=limit,
            offset=0,
        )

        events = []
        for execution in executions:
            if execution.get("customer_id") != str(customer_id):
                continue

            events.append(
                self._event(
                    type="workflow.execution",
                    timestamp=execution["created_at"],
                    title=(
                        execution.get("workflow_name")
                        or execution.get("template_name")
                        or "Workflow execution"
                    ),
                    description=execution.get("message"),
                    entity_id=execution.get("job_id"),
                    entity_type="workflow_execution",
                    metadata={
                        "job_id": str(execution.get("job_id")),
                        "workflow_run_id": (
                            str(execution.get("workflow_run_id"))
                            if execution.get("workflow_run_id") is not None
                            else None
                        ),
                        "status": execution.get("status"),
                        "conversation_id": execution.get("conversation_id"),
                        "ticket_id": execution.get("ticket_id"),
                        "channel": execution.get("channel"),
                        "subscription_name": execution.get("subscription_name"),
                        "trigger_event_type": execution.get("trigger_event_type"),
                    },
                )
            )

        return events

    def _event(
        self,
        *,
        type: str,
        timestamp,
        title: str,
        description: str | None = None,
        entity_id: UUID | None = None,
        entity_type: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        return {
            "type": type,
            "timestamp": timestamp,
            "title": title,
            "description": description,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "metadata": metadata or {},
        }

    def _value(self, value) -> str:
        return getattr(value, "value", str(value))
