from __future__ import annotations

from sqlalchemy import select, text

from uuid import UUID

from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.conversations import (
    ConversationCreate,
    ConversationMessageCreate,
    SenderType,
)
from app.domains.customer_service.schemas.tickets import TicketCreate
from app.domains.customer_service.services.sla import SLAService
from app.tenancy.models import Workspace

from app.domains.customer_service.repositories.chat_repository import (
    ChatRepository,
)
from app.domains.customer_service.services.customer_identity import (
    CustomerIdentityEvidence,
    CustomerIdentityService,
)


class CustomerChatService:
    def __init__(
        self,
        repository: ChatRepository,
    ):
        self.repository = repository

    async def create_session(
        self,
        *,
        user_id: UUID,
        visitor_id: str,
        channel: str = "website",
        customer_name: str | None = None,
        customer_email: str | None = None,
    ):
        return await self.repository.create_session(
            user_id=user_id,
            visitor_id=visitor_id,
            channel=channel,
            customer_name=customer_name,
            customer_email=customer_email,
        )

    async def get_session(
        self,
        *,
        session_id: UUID,
    ):
        return await self.repository.get_session(
            session_id=session_id,
        )

    async def save_pending_support_objective(
        self,
        *,
        session,
        pending: dict,
    ):
        meta = dict(session.meta or {})
        meta["pending_support_objective"] = pending

        return await self.repository.update_session_meta(
            session=session,
            meta=meta,
        )

    async def get_pending_support_objective(
        self,
        *,
        session,
    ) -> dict | None:
        return (session.meta or {}).get("pending_support_objective")

    async def clear_pending_support_objective(
        self,
        *,
        session,
    ):
        meta = dict(session.meta or {})
        meta.pop("pending_support_objective", None)

        return await self.repository.update_session_meta(
            session=session,
            meta=meta,
        )

    async def add_customer_message(
        self,
        *,
        session_id: UUID,
        content: str,
        client_message_id: str | None = None,
    ):
        return await self.repository.add_message(
            session_id=session_id,
            role="customer",
            content=content,
            client_message_id=client_message_id,
        )

    async def get_message_by_client_message_id(
        self,
        *,
        session_id: UUID,
        client_message_id: str,
    ):
        return await self.repository.get_message_by_client_message_id(
            session_id=session_id,
            client_message_id=client_message_id,
        )

    async def save_public_ingress_result(
        self,
        *,
        message,
        result: dict,
    ):
        meta = dict(message.meta or {})
        meta["public_ingress"] = result

        return await self.repository.update_message_meta(
            message=message,
            meta=meta,
        )

    async def add_ai_message(
        self,
        *,
        session_id: UUID,
        content: str,
        client_message_id: str | None = None,
    ):
        if client_message_id:
            existing = await self.repository.get_message_by_client_message_id(
                session_id=session_id,
                client_message_id=client_message_id,
            )
            if existing is not None:
                return existing

        return await self.repository.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            client_message_id=client_message_id,
        )

    async def get_messages(
        self,
        *,
        session_id: UUID,
    ):
        return await self.repository.list_messages(
            session_id=session_id,
        )

    async def get_or_create_widget_settings(
        self,
        *,
        user_id: UUID,
    ):
        return await self.repository.get_or_create_widget_settings(
            user_id=user_id,
        )

    async def get_widget_settings_by_public_key(
        self,
        *,
        public_key: str,
    ):
        return await self.repository.get_widget_settings_by_public_key(
            public_key=public_key,
        )

    async def update_widget_settings(
        self,
        *,
        user_id: UUID,
        values: dict,
    ):
        settings = await self.repository.get_or_create_widget_settings(
            user_id=user_id,
        )

        return await self.repository.update_widget_settings(
            settings=settings,
            values=values,
        )

    async def ensure_inbox_bridge_for_session(
        self,
        *,
        session,
    ):
        existing = await self.repository.get_inbox_link_for_session(
            session_id=session.id,
        )

        if existing is not None:
            return existing

        workspace_id = await self.repository.db.scalar(
            select(Workspace.id).where(Workspace.id == session.user_id)
        )
        if workspace_id:
            from app.domains.customer_service.services.commercial_operations import (
                CommercialOperationsService,
            )

            await CommercialOperationsService(
                self.repository.db, workspace_id=session.user_id
            ).require_monthly_conversation_quota()

        evidence = [
            CustomerIdentityEvidence(
                identity_type="website_visitor",
                value=session.visitor_id,
                namespace=f"website:{session.user_id}",
                source="website_chat",
            )
        ]

        if session.customer_email:
            evidence.append(
                CustomerIdentityEvidence(
                    identity_type="email",
                    value=session.customer_email,
                    namespace="global",
                    source="website_chat",
                )
            )

        customer = await CustomerIdentityService(self.repository.db).resolve_or_create(
            user_id=session.user_id,
            workspace_id=workspace_id,
            evidence=evidence,
            name=(session.customer_name or f"Website visitor {session.visitor_id}"),
            email=session.customer_email,
        )

        conversation = await ConversationRepository(self.repository.db).create(
            user_id=session.user_id,
            workspace_id=workspace_id,
            conversation=ConversationCreate(
                customer_id=customer.id,
                channel=session.channel,
                subject="Website chat",
            ),
        )

        ticket = await TicketRepository(self.repository.db).create(
            user_id=session.user_id,
            workspace_id=workspace_id,
            ticket=TicketCreate(
                conversation_id=conversation.id,
                title="Website chat",
                priority="normal",
                status="open",
                assigned_to=None,
            ),
        )

        await SLAService(self.repository.db).create_targets_for_ticket(
            ticket=ticket,
        )

        return await self.repository.create_inbox_link(
            user_id=session.user_id,
            chat_session_id=session.id,
            customer_id=customer.id,
            conversation_id=conversation.id,
            ticket_id=ticket.id,
        )

    async def add_inbox_customer_message_for_chat_session(
        self,
        *,
        session,
        chat_message,
    ):
        bridge = await self.ensure_inbox_bridge_for_session(
            session=session,
        )

        from app.domains.customer_service.services.inbox import InboxService

        return await InboxService(self.repository.db).add_message(
            conversation_id=bridge.conversation_id,
            payload=ConversationMessageCreate(
                sender_type=SenderType.CUSTOMER,
                body=chat_message.content,
                source_type="customer_chat",
                source_message_id=chat_message.id,
                meta={
                    "source": "customer_chat",
                    "chat_session_id": str(session.id),
                    "chat_message_id": str(chat_message.id),
                    "visitor_id": session.visitor_id,
                },
            ),
            commit=False,
            publish_realtime=False,
            run_customer_automation=False,
        )

    async def add_inbox_ai_message_for_chat_session(
        self,
        *,
        session,
        chat_message,
    ):
        bridge = await self.ensure_inbox_bridge_for_session(
            session=session,
        )

        from app.domains.customer_service.services.inbox import InboxService

        return await InboxService(self.repository.db).add_message(
            conversation_id=bridge.conversation_id,
            payload=ConversationMessageCreate(
                sender_type=SenderType.AI,
                body=chat_message.content,
                source_type="customer_chat",
                source_message_id=chat_message.id,
                meta={
                    "source": "customer_chat",
                    "chat_session_id": str(session.id),
                    "chat_message_id": str(chat_message.id),
                    "visitor_id": session.visitor_id,
                },
            ),
        )

    async def add_chat_assistant_message_for_conversation(
        self,
        *,
        conversation_id: UUID,
        content: str,
        source_message_id: UUID | None = None,
        source_sender_type: str = "agent",
    ):
        link = await self.repository.get_inbox_link_for_conversation(
            conversation_id=conversation_id,
        )

        if link is None:
            return None

        message = await self.repository.add_message(
            session_id=link.chat_session_id,
            role="assistant",
            content=content,
            meta={
                "source": "inbox_reply",
                "conversation_id": str(conversation_id),
                "conversation_message_id": (
                    str(source_message_id) if source_message_id is not None else None
                ),
                "sender_type": source_sender_type,
            },
        )

        return message

    async def acquire_public_ingress_lock(
        self,
        *,
        session_id: UUID,
        client_message_id: str,
    ) -> None:
        """
        Serialize one public-chat client message within the
        current database transaction.

        The lock and all subsequent ingress mutations are released
        atomically by commit/rollback of that transaction.
        """
        lock_key = f"public_chat_message:{session_id}:{client_message_id}"

        await self.repository.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )

    async def commit(self) -> None:
        """
        Commit the current customer-chat application transaction.

        HTTP adapters delegate transaction persistence here instead
        of manipulating the AsyncSession directly.
        """
        await self.repository.db.commit()
