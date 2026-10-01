from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    Integer,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.models import Base


class CustomerServiceRoutingPolicy(Base):
    __tablename__ = "cs_routing_policies"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_cs_routing_policy_name",
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
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    priority_rank: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False, index=True
    )
    is_fallback: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    strategy: Mapped[str] = mapped_column(
        String(50), default="least_loaded", nullable=False
    )
    candidate_assignee_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    candidate_team_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    candidate_queue_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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


class CustomerServiceAgent(Base):
    __tablename__ = "cs_agents"
    __table_args__ = (
        UniqueConstraint("user_id", "agent_user_id", name="uq_cs_agent_user"),
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

    agent_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False, index=True
    )
    availability: Mapped[str] = mapped_column(
        String(50), default="available", nullable=False, index=True
    )
    # ``availability`` remains the agent-selected/manual presence value.  The
    # fields below are workforce inputs used by AgentAvailabilityService.
    availability_source: Mapped[str] = mapped_column(
        String(20), default="manual", nullable=False
    )
    availability_mode: Mapped[str] = mapped_column(
        String(20), default="manual", nullable=False, index=True
    )
    last_presence_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    schedule_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    weekly_schedule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    channels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    languages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    max_open_tickets: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

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


class CustomerServiceAgentTimeOff(Base):
    __tablename__ = "cs_agent_time_off"
    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_id", "starts_at", "ends_at", name="uq_cs_agent_time_off_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cs_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CustomerServiceTeam(Base):
    __tablename__ = "cs_teams"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_cs_team_name"),)

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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
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


class CustomerServiceQueue(Base):
    __tablename__ = "cs_queues"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_cs_queue_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cs_teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    channel: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    priority_rank: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False, index=True
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CustomerServiceTeamMember(Base):
    __tablename__ = "cs_team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "agent_id", name="uq_cs_team_member"),
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

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cs_agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
