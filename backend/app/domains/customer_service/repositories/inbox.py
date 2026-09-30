from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    ConversationTag,
    Ticket,
)


class InboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self, user_id, *, folder: str = "inbox", limit: int = 100, offset: int = 0
    ):
        statement = (
            select(Conversation)
            .options(selectinload(Conversation.customer))
            .where(Conversation.user_id == user_id)
        )
        now = datetime.now(timezone.utc)
        if folder == "inbox":
            statement = statement.where(
                or_(
                    Conversation.snoozed_until.is_(None),
                    Conversation.snoozed_until <= now,
                ),
                Conversation.moderation_status == "normal",
            )
        elif folder == "snoozed":
            statement = statement.where(
                Conversation.snoozed_until > now,
                Conversation.moderation_status == "normal",
            )
        elif folder == "spam":
            statement = statement.where(Conversation.moderation_status != "normal")
        elif folder != "all":
            raise ValueError("Unknown inbox folder")
        result = await self.db.execute(
            statement.order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .offset(offset)
            .limit(limit)
        )

        conversations = result.scalars().unique().all()

        conversation_ids = [c.id for c in conversations]

        tickets_by_conversation_id = {}
        latest_message_by_conversation_id = {}
        tags_by_conversation_id = {}

        if conversation_ids:
            ticket_result = await self.db.execute(
                select(Ticket).where(Ticket.conversation_id.in_(conversation_ids))
            )

            tickets_by_conversation_id = {
                ticket.conversation_id: ticket
                for ticket in ticket_result.scalars().all()
            }

            tag_result = await self.db.execute(
                select(ConversationTag.conversation_id, ConversationTag.name)
                .where(
                    ConversationTag.user_id == user_id,
                    ConversationTag.conversation_id.in_(conversation_ids),
                )
                .order_by(ConversationTag.name.asc())
            )
            for conversation_id, tag_name in tag_result.all():
                tags_by_conversation_id.setdefault(conversation_id, []).append(tag_name)

            visible_sender_types = ("customer", "agent", "ai")

            ranked_messages = (
                select(
                    ConversationMessage.conversation_id.label("conversation_id"),
                    ConversationMessage.body.label("body"),
                    func.row_number()
                    .over(
                        partition_by=ConversationMessage.conversation_id,
                        order_by=(
                            ConversationMessage.created_at.desc(),
                            ConversationMessage.id.desc(),
                        ),
                    )
                    .label("rank"),
                )
                .where(
                    ConversationMessage.conversation_id.in_(conversation_ids),
                    ConversationMessage.sender_type.in_(visible_sender_types),
                )
                .subquery()
            )

            message_result = await self.db.execute(
                select(
                    ranked_messages.c.conversation_id,
                    ranked_messages.c.body,
                ).where(ranked_messages.c.rank == 1)
            )

            latest_message_by_conversation_id = {
                conversation_id: body for conversation_id, body in message_result.all()
            }

        items = []

        for conversation in conversations:
            latest_message = latest_message_by_conversation_id.get(conversation.id)

            ticket = tickets_by_conversation_id.get(conversation.id)

            items.append(
                {
                    "conversation_id": conversation.id,
                    "customer_id": conversation.customer_id,
                    "customer_name": conversation.customer.name
                    if conversation.customer
                    else None,
                    "customer_email": conversation.customer.email
                    if conversation.customer
                    else None,
                    "channel": conversation.channel,
                    "subject": conversation.subject,
                    "status": conversation.status.value
                    if hasattr(conversation.status, "value")
                    else conversation.status,
                    "latest_message": latest_message,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                    "snoozed_until": conversation.snoozed_until,
                    "moderation_status": conversation.moderation_status,
                    "moderation_reason": conversation.moderation_reason,
                    "tags": tags_by_conversation_id.get(conversation.id, []),
                    "ticket": (
                        {
                            "id": ticket.id,
                            "status": ticket.status.value
                            if hasattr(ticket.status, "value")
                            else ticket.status,
                            "priority": ticket.priority.value
                            if hasattr(ticket.priority, "value")
                            else ticket.priority,
                            "assigned_to": ticket.assigned_to,
                        }
                        if ticket
                        else None
                    ),
                }
            )

        return items
