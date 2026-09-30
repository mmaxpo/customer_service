from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceChannelConnection as ChannelConnection,
    CustomerServiceExternalConversationLink as ExternalConversationLink,
    CustomerServiceExternalMessageLink as ExternalMessageLink,
    CustomerServiceExternalMediaLink as ExternalMediaLink,
)


class OmnichannelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_connection(
        self,
        *,
        user_id: UUID,
        channel: str,
        external_account_id: str,
        display_name: str | None = None,
        status: str = "active",
        config: dict | None = None,
    ) -> ChannelConnection:
        existing = await self.get_connection(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
        )
        if existing is not None:
            return existing

        connection = ChannelConnection(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            display_name=display_name,
            status=status,
            config=config or {},
        )
        self.db.add(connection)
        await self.db.flush()
        await self.db.refresh(connection)
        return connection

    async def get_connection(
        self,
        *,
        user_id: UUID,
        channel: str,
        external_account_id: str,
    ) -> ChannelConnection | None:
        result = await self.db.execute(
            select(ChannelConnection).where(
                ChannelConnection.user_id == user_id,
                ChannelConnection.channel == channel,
                ChannelConnection.external_account_id == external_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_connections(self, user_id: UUID) -> list[ChannelConnection]:
        result = await self.db.execute(
            select(ChannelConnection)
            .where(ChannelConnection.user_id == user_id)
            .order_by(ChannelConnection.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_external_conversation(
        self,
        *,
        user_id: UUID,
        channel: str,
        external_account_id: str,
        external_thread_id: str,
    ) -> ExternalConversationLink | None:
        result = await self.db.execute(
            select(ExternalConversationLink).where(
                ExternalConversationLink.user_id == user_id,
                ExternalConversationLink.channel == channel,
                ExternalConversationLink.external_account_id == external_account_id,
                ExternalConversationLink.external_thread_id == external_thread_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_external_conversation(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        customer_id: UUID | None,
        channel: str,
        external_account_id: str,
        external_thread_id: str,
        external_customer_id: str | None = None,
        meta: dict | None = None,
    ) -> ExternalConversationLink:
        existing = await self.get_external_conversation(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            external_thread_id=external_thread_id,
        )
        if existing is not None:
            return existing

        link = ExternalConversationLink(
            user_id=user_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            channel=channel,
            external_account_id=external_account_id,
            external_thread_id=external_thread_id,
            external_customer_id=external_customer_id,
            meta=meta or {},
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def get_external_conversation_by_conversation_id(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
    ) -> ExternalConversationLink | None:
        result = await self.db.execute(
            select(ExternalConversationLink).where(
                ExternalConversationLink.user_id == user_id,
                ExternalConversationLink.conversation_id == conversation_id,
            )
        )
        return result.scalar_one_or_none()

    async def link_external_conversation(self, **kwargs):

        existing = await self.get_external_conversation(
            user_id=kwargs["user_id"],
            channel=kwargs["channel"],
            external_account_id=kwargs["external_account_id"],
            external_thread_id=kwargs["external_thread_id"],
        )

        if existing is not None:
            return existing

        stmt = (
            pg_insert(ExternalConversationLink)
            .values(**kwargs)
            .on_conflict_do_nothing(constraint="uq_cs_external_conversation_thread")
            .returning(ExternalConversationLink)
        )

        result = await self.db.execute(stmt)

        created = result.scalar_one_or_none()

        if created is not None:
            return created

        existing = await self.get_external_conversation(
            user_id=kwargs["user_id"],
            channel=kwargs["channel"],
            external_account_id=kwargs["external_account_id"],
            external_thread_id=kwargs["external_thread_id"],
        )

        if existing is None:
            raise RuntimeError(
                "External conversation link conflict was not recoverable."
            )

        return existing

    async def find_outbound_message_by_idempotency_key(
        self,
        *,
        user_id,
        channel: str,
        external_account_id: str,
        idempotency_key: str,
    ):
        """
        Return an existing outbound external message link for this idempotency key.

        We intentionally store/read this from JSON meta so this hardening does not
        require a schema migration. It protects retries where the provider already
        accepted the send and the same idempotency key is submitted again.
        """
        if not idempotency_key:
            return None

        result = await self.db.execute(
            select(ExternalMessageLink).where(
                ExternalMessageLink.user_id == user_id,
                ExternalMessageLink.channel == channel,
                ExternalMessageLink.external_account_id == external_account_id,
                ExternalMessageLink.direction == "outbound",
            )
        )

        for link in result.scalars().all():
            omnichannel_meta = (link.meta or {}).get("omnichannel") or {}
            if omnichannel_meta.get("idempotency_key") == idempotency_key:
                return link

        return None

    async def get_external_message(
        self,
        *,
        user_id,
        channel: str,
        external_account_id: str,
        external_message_id: str,
    ):
        result = await self.db.execute(
            select(ExternalMessageLink).where(
                ExternalMessageLink.user_id == user_id,
                ExternalMessageLink.channel == channel,
                ExternalMessageLink.external_account_id == external_account_id,
                ExternalMessageLink.external_message_id == external_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def link_external_message(self, **kwargs):
        existing = await self.get_external_message(
            user_id=kwargs["user_id"],
            channel=kwargs["channel"],
            external_account_id=kwargs["external_account_id"],
            external_message_id=kwargs["external_message_id"],
        )

        if existing is not None:
            return existing

        stmt = (
            pg_insert(ExternalMessageLink)
            .values(**kwargs)
            .on_conflict_do_nothing(constraint="uq_cs_external_message")
            .returning(ExternalMessageLink)
        )

        result = await self.db.execute(stmt)
        created = result.scalar_one_or_none()

        if created is not None:
            return created

        existing = await self.get_external_message(
            user_id=kwargs["user_id"],
            channel=kwargs["channel"],
            external_account_id=kwargs["external_account_id"],
            external_message_id=kwargs["external_message_id"],
        )

        if existing is None:
            raise RuntimeError("External message link conflict was not recoverable.")

        return existing

    async def get_external_media(
        self,
        *,
        user_id: UUID,
        channel: str,
        external_account_id: str,
        external_message_id: str,
        provider_media_id: str,
    ) -> ExternalMediaLink | None:
        result = await self.db.execute(
            select(ExternalMediaLink).where(
                ExternalMediaLink.user_id == user_id,
                ExternalMediaLink.channel == channel,
                ExternalMediaLink.external_account_id == external_account_id,
                ExternalMediaLink.external_message_id == external_message_id,
                ExternalMediaLink.provider_media_id == provider_media_id,
            )
        )
        return result.scalar_one_or_none()

    async def link_external_media(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        attachment_id: UUID,
        channel: str,
        external_account_id: str,
        external_message_id: str,
        provider_media_id: str,
        meta: dict | None = None,
    ) -> ExternalMediaLink:
        existing = await self.get_external_media(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            external_message_id=external_message_id,
            provider_media_id=provider_media_id,
        )

        if existing is not None:
            return existing

        stmt = (
            pg_insert(ExternalMediaLink)
            .values(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=message_id,
                attachment_id=attachment_id,
                channel=channel,
                external_account_id=external_account_id,
                external_message_id=external_message_id,
                provider_media_id=provider_media_id,
                meta=meta or {},
            )
            .on_conflict_do_nothing(constraint="uq_cs_external_media")
            .returning(ExternalMediaLink)
        )

        result = await self.db.execute(stmt)
        created = result.scalar_one_or_none()

        if created is not None:
            return created

        existing = await self.get_external_media(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            external_message_id=external_message_id,
            provider_media_id=provider_media_id,
        )

        if existing is None:
            raise RuntimeError("External media link conflict was not recoverable.")

        return existing

    async def create_external_message(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        channel: str,
        external_account_id: str,
        external_thread_id: str,
        external_message_id: str,
        direction: str,
        delivery_status: str = "received",
        meta: dict | None = None,
    ) -> ExternalMessageLink:
        existing = await self.get_external_message(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            external_message_id=external_message_id,
        )
        if existing is not None:
            return existing

        link = ExternalMessageLink(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            channel=channel,
            external_account_id=external_account_id,
            external_thread_id=external_thread_id,
            external_message_id=external_message_id,
            direction=direction,
            delivery_status=delivery_status,
            meta=meta or {},
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def find_customer_by_email(
        self,
        *,
        user_id: UUID,
        email: str | None,
    ):
        if not email:
            return None

        from app.domains.customer_service.models import Customer

        result = await self.db.execute(
            select(Customer).where(
                Customer.user_id == user_id,
                Customer.email == email,
            )
        )
        return result.scalar_one_or_none()

    async def create_customer(
        self,
        *,
        user_id: UUID,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ):
        from app.domains.customer_service.models import Customer

        from app.tenancy.models import Workspace

        workspace_id = await self.db.scalar(
            select(Workspace.id).where(Workspace.id == user_id)
        )
        customer = Customer(
            user_id=user_id,
            workspace_id=workspace_id,
            name=name,
            email=email,
            phone=phone,
        )
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)
        return customer

    async def create_conversation(
        self,
        *,
        user_id: UUID,
        customer_id: UUID,
        channel: str,
        subject: str | None = None,
    ):
        from app.domains.customer_service.models import Conversation

        from app.tenancy.models import Workspace

        workspace_id = await self.db.scalar(
            select(Workspace.id).where(Workspace.id == user_id)
        )
        if workspace_id:
            from app.domains.customer_service.services.commercial_operations import (
                CommercialOperationsService,
            )

            await CommercialOperationsService(
                self.db, workspace_id=user_id
            ).require_monthly_conversation_quota()
        conversation = Conversation(
            user_id=user_id,
            workspace_id=workspace_id,
            customer_id=customer_id,
            channel=channel,
            subject=subject,
        )
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def create_message(
        self,
        *,
        conversation_id: UUID,
        sender_type,
        body: str,
        meta: dict | None = None,
    ):
        from app.domains.customer_service.models import ConversationMessage

        message = ConversationMessage(
            conversation_id=conversation_id,
            sender_type=sender_type,
            body=body,
            meta=meta,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def create_ticket(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        title: str,
    ):
        from app.domains.customer_service.models import Ticket

        from app.tenancy.models import Workspace

        workspace_id = await self.db.scalar(
            select(Workspace.id).where(Workspace.id == user_id)
        )
        ticket = Ticket(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            title=title,
        )
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def update_external_message_delivery_status(
        self,
        *,
        user_id: UUID,
        channel: str,
        external_account_id: str,
        external_message_id: str,
        delivery_status: str,
        meta: dict | None = None,
    ) -> ExternalMessageLink | None:
        link = await self.get_external_message(
            user_id=user_id,
            channel=channel,
            external_account_id=external_account_id,
            external_message_id=external_message_id,
        )
        if link is None:
            return None

        link.delivery_status = delivery_status

        current_meta = dict(link.meta or {})
        if meta:
            current_meta.update(meta)

            delivery_history = list(current_meta.get("delivery_history") or [])
            delivery_event = meta.get("delivery_event")
            if delivery_event is not None:
                delivery_history.append(
                    {
                        "status": delivery_status,
                        **delivery_event,
                    }
                )
                current_meta["delivery_history"] = delivery_history

        link.meta = current_meta

        await self.db.flush()
        await self.db.refresh(link)
        return link
