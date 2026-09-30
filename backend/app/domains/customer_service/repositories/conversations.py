from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
)
from app.domains.customer_service.schemas.conversations import (
    ConversationCreate,
    ConversationMessageCreate,
)

from app.domains.customer_service.models.tickets import (
    ConversationTag,
    Ticket,
    TicketAssignment,
)
from app.domains.customer_service.models.quality import (
    AgentAssistSuggestion,
    AgentAssistSuggestionRevision,
    CustomerServiceConversationInsight,
    CustomerServiceQualityReview,
    CustomerServiceSuggestedAction,
)
from app.domains.customer_service.models.omnichannel import (
    CustomerServiceExternalConversationLink,
    CustomerServiceExternalMessageLink,
)
from app.domains.customer_service.models.chat import CustomerChatInboxLink
from app.domains.customer_service.models.sla import SLAViolation


@dataclass(frozen=True)
class ConversationMessageWriteResult:
    message: ConversationMessage
    created: bool


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id):
        return await self.db.get(Conversation, conversation_id)

    async def get_for_user(self, *, user_id, conversation_id):
        return await self.db.scalar(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )

    async def create(
        self,
        user_id,
        conversation: ConversationCreate,
        *,
        workspace_id=None,
    ):
        obj = Conversation(
            user_id=user_id,
            workspace_id=workspace_id,
            customer_id=conversation.customer_id,
            channel=conversation.channel,
            subject=conversation.subject,
        )

        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def list(
        self, user_id, *, limit: int = 100, offset: int = 0, shopify_connection_id=None
    ):
        statement = select(Conversation).where(Conversation.user_id == user_id)
        if shopify_connection_id is not None:
            statement = statement.join(
                CustomerServiceExternalConversationLink,
                CustomerServiceExternalConversationLink.conversation_id
                == Conversation.id,
            ).where(
                CustomerServiceExternalConversationLink.user_id == user_id,
                CustomerServiceExternalConversationLink.channel == "shopify",
                CustomerServiceExternalConversationLink.external_account_id
                == str(shopify_connection_id),
            )
        result = await self.db.execute(
            statement.order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().unique().all()

    async def get_detail(self, user_id, conversation_id):
        result = await self.db.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.customer),
                selectinload(Conversation.messages),
                selectinload(Conversation.ticket),
            )
            .where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )
        return result.scalars().unique().one_or_none()

    async def delete_for_user(self, *, user_id, conversation_id) -> bool:
        conversation = await self.db.scalar(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )

        if conversation is None:
            return False

        ticket_ids = list(
            await self.db.scalars(
                select(Ticket.id).where(
                    Ticket.user_id == user_id,
                    Ticket.conversation_id == conversation_id,
                )
            )
        )

        suggestion_ids = list(
            await self.db.scalars(
                select(AgentAssistSuggestion.id).where(
                    AgentAssistSuggestion.conversation_id == conversation_id,
                )
            )
        )

        if suggestion_ids:
            await self.db.execute(
                delete(AgentAssistSuggestionRevision).where(
                    AgentAssistSuggestionRevision.suggestion_id.in_(suggestion_ids)
                )
            )

        if ticket_ids:
            await self.db.execute(
                delete(SLAViolation).where(SLAViolation.ticket_id.in_(ticket_ids))
            )
            await self.db.execute(
                delete(TicketAssignment).where(
                    TicketAssignment.ticket_id.in_(ticket_ids)
                )
            )
            await self.db.execute(
                delete(CustomerChatInboxLink).where(
                    CustomerChatInboxLink.ticket_id.in_(ticket_ids)
                )
            )

        await self.db.execute(
            delete(CustomerServiceExternalMessageLink).where(
                CustomerServiceExternalMessageLink.conversation_id == conversation_id
            )
        )
        await self.db.execute(
            delete(CustomerServiceExternalConversationLink).where(
                CustomerServiceExternalConversationLink.conversation_id
                == conversation_id
            )
        )
        await self.db.execute(
            delete(CustomerChatInboxLink).where(
                CustomerChatInboxLink.conversation_id == conversation_id
            )
        )
        await self.db.execute(
            delete(ConversationTag).where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id == conversation_id,
            )
        )
        await self.db.execute(
            delete(CustomerServiceConversationInsight).where(
                CustomerServiceConversationInsight.user_id == user_id,
                CustomerServiceConversationInsight.conversation_id == conversation_id,
            )
        )
        await self.db.execute(
            delete(CustomerServiceSuggestedAction).where(
                CustomerServiceSuggestedAction.user_id == user_id,
                CustomerServiceSuggestedAction.conversation_id == conversation_id,
            )
        )
        await self.db.execute(
            delete(CustomerServiceQualityReview).where(
                CustomerServiceQualityReview.user_id == user_id,
                CustomerServiceQualityReview.conversation_id == conversation_id,
            )
        )
        await self.db.execute(
            delete(AgentAssistSuggestion).where(
                AgentAssistSuggestion.conversation_id == conversation_id,
            )
        )

        if ticket_ids:
            await self.db.execute(
                delete(Ticket).where(
                    Ticket.user_id == user_id,
                    Ticket.id.in_(ticket_ids),
                )
            )

        await self.db.delete(conversation)
        await self.db.commit()

        return True

    async def list_recent_context_messages(
        self,
        *,
        user_id,
        conversation_id,
        limit: int = 30,
        include_internal_notes: bool = False,
    ):
        conversation_exists = await self.db.scalar(
            select(Conversation.id).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )

        if conversation_exists is None:
            return None

        query = select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id,
        )

        if not include_internal_notes:
            query = query.where(ConversationMessage.sender_type != "internal_note")

        result = await self.db.execute(
            query.order_by(
                ConversationMessage.created_at.desc(),
                ConversationMessage.id.desc(),
            ).limit(limit)
        )

        return list(reversed(result.scalars().all()))

    async def get_latest_workflow_message_meta(
        self,
        *,
        user_id,
        conversation_id,
        limit: int = 30,
    ):
        messages = await self.list_recent_context_messages(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit,
            include_internal_notes=False,
        )

        if messages is None:
            return None

        for message in reversed(messages):
            workflow = (message.meta or {}).get("workflow")
            if workflow:
                return workflow

        return {}

    async def get_latest_customer_message(
        self,
        *,
        user_id,
        conversation_id,
    ):
        conversation_exists = await self.db.scalar(
            select(Conversation.id).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )

        if conversation_exists is None:
            return None

        result = await self.db.execute(
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.sender_type == "customer",
            )
            .order_by(
                ConversationMessage.created_at.desc(),
                ConversationMessage.id.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def list_messages(
        self,
        *,
        user_id,
        conversation_id,
        limit: int = 100,
        offset: int = 0,
    ):
        conversation_exists = await self.db.scalar(
            select(Conversation.id).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )

        if conversation_exists is None:
            return None

        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(
                ConversationMessage.created_at.asc(),
                ConversationMessage.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )

        return result.scalars().all()

    async def get_message_by_source_identity(
        self,
        *,
        conversation_id,
        source_type: str,
        source_message_id,
    ):
        result = await self.db.execute(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.source_type == source_type,
                ConversationMessage.source_message_id == source_message_id,
            )
        )

        return result.scalar_one_or_none()

    async def add_message(
        self,
        conversation_id,
        message: ConversationMessageCreate,
        *,
        commit: bool = True,
    ):
        result = await self.add_message_with_result(
            conversation_id=conversation_id,
            message=message,
            commit=commit,
        )
        return result.message

    async def add_message_with_result(
        self,
        conversation_id,
        message: ConversationMessageCreate,
        *,
        commit: bool = True,
    ) -> ConversationMessageWriteResult:
        """
        Persist a conversation message and report whether this call
        actually created the durable row.

        Source-identified messages are get-or-create:

        - existing source identity -> created=False
        - successful insert         -> created=True
        - concurrent unique race    -> created=False

        The database unique index remains the authoritative race guard.
        """
        source_type = str(message.source_type).strip() if message.source_type else None
        source_message_id = message.source_message_id

        # Durable source identity is an atomic pair.
        #
        # Allow:
        #   source_type=None, source_message_id=None
        #   source_type=<value>, source_message_id=<uuid>
        #
        # Reject partial/blank identities because they cannot participate
        # safely in the database uniqueness contract.
        if source_type == "":
            source_type = None

        if (source_type is None) != (source_message_id is None):
            raise ValueError(
                "source_type and source_message_id must be provided together"
            )

        if source_type and source_message_id:
            existing = await self.get_message_by_source_identity(
                conversation_id=conversation_id,
                source_type=source_type,
                source_message_id=source_message_id,
            )

            if existing is not None:
                return ConversationMessageWriteResult(
                    message=existing,
                    created=False,
                )

        conversation = await self.db.get(
            Conversation,
            conversation_id,
        )

        obj = ConversationMessage(
            conversation_id=conversation_id,
            source_type=source_type,
            source_message_id=source_message_id,
            sender_type=message.sender_type,
            body=message.body,
            meta=getattr(message, "meta", None),
            created_at=datetime.now(timezone.utc),
        )

        try:
            async with self.db.begin_nested():
                self.db.add(obj)
                await self.db.flush()

        except IntegrityError:
            if not (source_type and source_message_id):
                raise

            existing = await self.get_message_by_source_identity(
                conversation_id=conversation_id,
                source_type=source_type,
                source_message_id=source_message_id,
            )

            if existing is None:
                raise

            return ConversationMessageWriteResult(
                message=existing,
                created=False,
            )

        if conversation is not None:
            conversation.updated_at = func.now()

        if commit:
            await self.db.commit()
            await self.db.refresh(obj)

        return ConversationMessageWriteResult(
            message=obj,
            created=True,
        )

    async def update_message_meta(self, message_id, meta: dict):
        message = await self.db.get(ConversationMessage, message_id)

        if message is None:
            return None

        message.meta = meta
        await self.db.commit()
        await self.db.refresh(message)
        return message
