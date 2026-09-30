from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domains.customer_service.models.enums import (
    ConversationStatus,
    CustomerStatus,
    MessageSenderType,
)
from app.models.models import Base

if TYPE_CHECKING:
    from app.domains.customer_service.models.tickets import Ticket


class Customer(Base):
    __tablename__ = "cs_customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )

    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus), default=CustomerStatus.ACTIVE
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cs_customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    consent: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    anonymized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="customer"
    )


class CustomerIdentity(Base):
    __tablename__ = "cs_customer_identities"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "identity_type",
            "namespace",
            "normalized_value",
            name="uq_cs_customer_identity_scope",
        ),
        Index(
            "ix_cs_customer_identities_customer",
            "user_id",
            "customer_id",
        ),
        Index(
            "ix_cs_customer_identities_lookup",
            "user_id",
            "identity_type",
            "namespace",
            "normalized_value",
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

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cs_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    identity_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    namespace: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        default="global",
    )

    value: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    normalized_value: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    external_account_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    source: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Conversation(Base):
    __tablename__ = "cs_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_customers.id"), index=True
    )

    channel: Mapped[str] = mapped_column(String(64), default="web")
    subject: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.OPEN
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cs_conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    snoozed_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    snooze_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snoozed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    moderation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="normal", index=True
    )
    moderation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    moderation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    customer: Mapped["Customer"] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    ticket: Mapped["Ticket | None"] = relationship(back_populates="conversation")


class ConversationMessage(Base):
    __tablename__ = "cs_conversation_messages"

    __table_args__ = (
        Index(
            "uq_cs_conversation_messages_source_identity",
            "conversation_id",
            "source_type",
            "source_message_id",
            unique=True,
            postgresql_where=text("source_message_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id"), index=True
    )

    source_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    sender_type: Mapped[MessageSenderType] = mapped_column(
        Enum(
            MessageSenderType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="messagesendertype",
        )
    )
    body: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
