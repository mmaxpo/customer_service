from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domains.customer_service.models.enums import AgentAssistSuggestionStatus
from app.models.models import Base


class AgentAssistSuggestion(Base):
    __tablename__ = "cs_agent_assist_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id"),
        index=True,
        nullable=False,
    )

    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cs_conversation_messages.id"),
        nullable=True,
    )

    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)

    original_suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    current_suggestion: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[AgentAssistSuggestionStatus] = mapped_column(
        Enum(
            AgentAssistSuggestionStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="agentassistsuggestionstatus",
        ),
        default=AgentAssistSuggestionStatus.GENERATED,
        nullable=False,
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    sent_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cs_conversation_messages.id"),
        nullable=True,
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


class AgentAssistSuggestionRevision(Base):
    __tablename__ = "cs_agent_assist_suggestion_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_agent_assist_suggestions.id"),
        index=True,
        nullable=False,
    )

    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CustomerServiceConversationInsight(Base):
    __tablename__ = "cs_conversation_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id"),
        index=True,
        nullable=False,
    )

    sentiment: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    intent: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    urgency: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)

    entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    opportunities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped[str] = mapped_column(String(50), default="rule", nullable=False)

    language: Mapped[str] = mapped_column(String(16), default="und", nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CustomerServiceSuggestedAction(Base):
    __tablename__ = "cs_suggested_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id"), nullable=False, index=True
    )

    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    status: Mapped[str] = mapped_column(String(50), default="suggested", index=True)

    source: Mapped[str] = mapped_column(String(50), default="rule")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CustomerServiceQualityReview(Base):
    __tablename__ = "cs_quality_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_conversations.id"), nullable=False, index=True
    )

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    issues: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    reviewer_type: Mapped[str] = mapped_column(String(50), default="rule")

    reply_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    review_type: Mapped[str] = mapped_column(
        String(50),
        default="ai_reply",
        nullable=False,
        index=True,
    )

    outcome: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tone_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    draft_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    edit_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
