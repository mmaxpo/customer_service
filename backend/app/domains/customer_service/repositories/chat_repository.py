from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.domains.customer_service.models import (
    CustomerChatSession,
    CustomerChatMessage,
    CustomerChatWidgetSettings,
    CustomerChatInboxLink,
    Conversation,
)


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        *,
        user_id: uuid.UUID,
        visitor_id: str,
        channel: str = "website",
        customer_name: str | None = None,
        customer_email: str | None = None,
    ) -> CustomerChatSession:

        session = CustomerChatSession(
            user_id=user_id,
            visitor_id=visitor_id,
            channel=channel,
            customer_name=customer_name,
            customer_email=customer_email,
        )

        self.db.add(session)

        await self.db.flush()
        await self.db.refresh(session)

        return session

    async def get_session(
        self,
        session_id: uuid.UUID,
    ) -> CustomerChatSession | None:

        result = await self.db.execute(
            select(CustomerChatSession).where(CustomerChatSession.id == session_id)
        )

        return result.scalar_one_or_none()

    async def update_session_meta(
        self,
        *,
        session: CustomerChatSession,
        meta: dict,
    ) -> CustomerChatSession:
        session.meta = meta
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def add_message(
        self,
        *,
        session_id: uuid.UUID,
        role: str,
        content: str,
        meta: dict | None = None,
        client_message_id: str | None = None,
    ) -> CustomerChatMessage:

        if client_message_id:
            existing = await self.get_message_by_client_message_id(
                session_id=session_id,
                client_message_id=client_message_id,
            )
            if existing is not None:
                return existing

        message = CustomerChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            meta=meta,
            client_message_id=client_message_id,
        )

        try:
            async with self.db.begin_nested():
                self.db.add(message)
                await self.db.flush()

        except IntegrityError:
            if not client_message_id:
                raise

            existing = await self.get_message_by_client_message_id(
                session_id=session_id,
                client_message_id=client_message_id,
            )

            if existing is None:
                raise

            return existing

        await self.db.refresh(message)

        return message

    async def get_message_by_client_message_id(
        self,
        *,
        session_id: uuid.UUID,
        client_message_id: str,
    ) -> CustomerChatMessage | None:
        result = await self.db.execute(
            select(CustomerChatMessage).where(
                CustomerChatMessage.session_id == session_id,
                CustomerChatMessage.client_message_id == client_message_id,
            )
        )

        return result.scalar_one_or_none()

    async def update_message_meta(
        self,
        *,
        message: CustomerChatMessage,
        meta: dict,
    ) -> CustomerChatMessage:
        message.meta = meta
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def list_messages(
        self,
        session_id: uuid.UUID,
    ) -> list[CustomerChatMessage]:

        result = await self.db.execute(
            select(CustomerChatMessage)
            .where(CustomerChatMessage.session_id == session_id)
            .order_by(CustomerChatMessage.created_at.asc())
        )

        return list(result.scalars().all())

    async def get_widget_settings(
        self,
        *,
        user_id: uuid.UUID,
    ) -> CustomerChatWidgetSettings | None:
        result = await self.db.execute(
            select(CustomerChatWidgetSettings).where(
                CustomerChatWidgetSettings.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_widget_settings(
        self,
        *,
        user_id: uuid.UUID,
    ) -> CustomerChatWidgetSettings:
        settings = await self.get_widget_settings(user_id=user_id)
        if settings is not None:
            return settings

        settings = CustomerChatWidgetSettings(user_id=user_id)
        self.db.add(settings)

        try:
            await self.db.flush()
            await self.db.refresh(settings)
            return settings
        except IntegrityError:
            await self.db.rollback()
            existing = await self.get_widget_settings(user_id=user_id)
            if existing is None:
                raise
            return existing

    async def get_widget_settings_by_public_key(
        self,
        *,
        public_key: str,
    ) -> CustomerChatWidgetSettings | None:
        result = await self.db.execute(
            select(CustomerChatWidgetSettings).where(
                CustomerChatWidgetSettings.public_key == public_key
            )
        )
        return result.scalar_one_or_none()

    async def update_widget_settings(
        self,
        *,
        settings: CustomerChatWidgetSettings,
        values: dict,
    ) -> CustomerChatWidgetSettings:
        for key, value in values.items():
            setattr(settings, key, value)

        await self.db.flush()
        await self.db.refresh(settings)
        return settings

    async def get_inbox_link_for_session(
        self,
        *,
        session_id: uuid.UUID,
    ) -> CustomerChatInboxLink | None:
        result = await self.db.execute(
            select(CustomerChatInboxLink).where(
                CustomerChatInboxLink.chat_session_id == session_id
            )
        )
        return result.scalar_one_or_none()

    async def create_inbox_link(
        self,
        *,
        user_id: uuid.UUID,
        chat_session_id: uuid.UUID,
        customer_id: uuid.UUID,
        conversation_id: uuid.UUID,
        ticket_id: uuid.UUID,
    ) -> CustomerChatInboxLink:
        link = CustomerChatInboxLink(
            user_id=user_id,
            chat_session_id=chat_session_id,
            customer_id=customer_id,
            conversation_id=conversation_id,
            ticket_id=ticket_id,
        )

        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def get_inbox_link_for_conversation(
        self,
        *,
        conversation_id: uuid.UUID,
    ) -> CustomerChatInboxLink | None:
        result = await self.db.execute(
            select(CustomerChatInboxLink)
            .join(Conversation, Conversation.id == CustomerChatInboxLink.conversation_id)
            .where(
                (CustomerChatInboxLink.conversation_id == conversation_id)
                | (Conversation.merged_into_id == conversation_id)
            )
            .order_by(CustomerChatInboxLink.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
