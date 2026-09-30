from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.models import Base


class CustomerServiceChannelConnection(Base):
    __tablename__ = "cs_channel_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "external_account_id",
            name="uq_cs_channel_connection_account",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )

    channel: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CustomerServiceExternalConversationLink(Base):
    __tablename__ = "cs_external_conversation_links"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "external_account_id",
            "external_thread_id",
            name="uq_cs_external_conversation_thread",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id"), index=True, nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_customers.id"), index=True, nullable=False
    )

    channel: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CustomerServiceExternalMessageLink(Base):
    __tablename__ = "cs_external_message_links"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "external_account_id",
            "external_message_id",
            name="uq_cs_external_message",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id"), index=True, nullable=False
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversation_messages.id"), index=True, nullable=False
    )

    channel: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str] = mapped_column(
        String(32), default="inbound", nullable=False
    )
    delivery_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CustomerServiceExternalMediaLink(Base):
    __tablename__ = "cs_external_media_links"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "external_account_id",
            "external_message_id",
            "provider_media_id",
            name="uq_cs_external_media",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=False,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "cs_conversations.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "cs_conversation_messages.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "cs_attachments.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
        unique=True,
    )

    channel: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )

    external_account_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    external_message_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    provider_media_id: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    meta: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CustomerServiceEventSubscription(Base):
    __tablename__ = "cs_event_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_type",
            "name",
            name="uq_cs_event_subscription_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cs_workflow_templates.id"),
        nullable=True,
        index=True,
    )

    workflow_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
