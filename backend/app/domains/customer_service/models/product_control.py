from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.models import Base


class CustomerServiceAutopilotPolicy(Base):
    """Workspace-owned guardrails for one customer-service intent."""

    __tablename__ = "cs_autopilot_policies"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "intent",
            name="uq_cs_autopilot_policy_workspace_intent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intent: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft_reply"
    )
    minimum_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.85
    )
    maximum_auto_risk: Mapped[str] = mapped_column(
        String(16), nullable=False, default="low"
    )
    allowed_channels: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: ["email", "website_chat"]
    )
    allowed_languages: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: ["*"]
    )
    mutation_requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CustomerServiceProactivePolicy(Base):
    __tablename__ = "cs_proactive_policies"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "signal", name="uq_cs_proactive_policy_workspace_signal"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal: Mapped[str] = mapped_column(String(80), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lookback_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=720)
    cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    action: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CustomerServiceProactiveIncident(Base):
    __tablename__ = "cs_proactive_incidents"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "fingerprint", name="uq_cs_proactive_incident_fingerprint"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cs_proactive_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cs_conversations.id", ondelete="SET NULL"),
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cs_customers.id", ondelete="SET NULL"),
        index=True,
    )
    provider_id: Mapped[str | None] = mapped_column(String(255))
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    action_taken: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
