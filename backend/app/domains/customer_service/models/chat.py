from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
    Integer,
    Boolean,
    Float,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domains.customer_service.models.enums import (
    CustomerStatus,
    SLAViolationStatus,
    TicketStatus,
    TicketPriority,
    SLATargetType,
    AgentAssistSuggestionStatus,
    MessageSenderType,
    ConversationStatus,
)
from app.models.models import Base


class CustomerChatWidgetSettings(Base):
    __tablename__ = "cs_chat_widget_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
    )

    public_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: f"cw_{uuid.uuid4().hex}",
    )

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    title: Mapped[str] = mapped_column(
        String(120), default="Chat with us", nullable=False
    )
    welcome_message: Mapped[str] = mapped_column(
        Text,
        default="Hi! How can we help you today?",
        nullable=False,
    )
    brand_color: Mapped[str] = mapped_column(
        String(32), default="#16a34a", nullable=False
    )
    position: Mapped[str] = mapped_column(
        String(32), default="bottom-right", nullable=False
    )
    assistant_name: Mapped[str] = mapped_column(
        String(120), default="Tajeran AI", nullable=False
    )
    auto_answer_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    auto_answer_confidence_threshold: Mapped[float] = mapped_column(
        Float,
        default=0.75,
        nullable=False,
    )
    human_handoff_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    human_handoff_message: Mapped[str] = mapped_column(
        Text,
        default="I’ll connect you with our support team now.",
        nullable=False,
    )
    workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
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


class CustomerChatSession(Base):
    __tablename__ = "cs_chat_sessions"

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

    channel: Mapped[str] = mapped_column(
        String(64),
        default="website",
        nullable=False,
        index=True,
    )

    visitor_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    customer_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        index=True,
    )

    customer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="open",
        nullable=False,
        index=True,
    )

    meta: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["CustomerChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class CustomerChatInboxLink(Base):
    __tablename__ = "cs_chat_inbox_links"

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

    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_tickets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class CustomerChatMessage(Base):
    __tablename__ = "cs_chat_messages"

    __table_args__ = (
        Index(
            "uq_cs_chat_messages_session_client_message_id",
            "session_id",
            "client_message_id",
            unique=True,
            postgresql_where=text(
                "client_message_id IS NOT NULL"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_chat_sessions.id"),
        nullable=False,
        index=True,
    )

    client_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
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

    session: Mapped["CustomerChatSession"] = relationship(
        back_populates="messages",
    )
