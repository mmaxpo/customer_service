"""
Improvements applied:
1. Audit columns - created_at, updated_at with TZ awareness.
2. Deterministic naming - global MetaData carries a naming convention so Alembic migrations are stable.
3. Explicit title index - Index(...) for fast look-ups.
"""

from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Column,
    MetaData,
    String,
    Integer,
    Text,
    func,
    Index,
    Boolean,
    DateTime,
    event,
    ForeignKey,
    Float,
    UniqueConstraint,
)
from typing import Any
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.dialects.postgresql import JSONB


# Global naming convention → Alembic generates readable constraint names
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata


class User(Base):
    __tablename__ = "user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    normalized_email = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    terms_version = Column(String(length=64), nullable=True)
    privacy_accepted_at = Column(DateTime(timezone=True), nullable=True)
    privacy_version = Column(String(length=64), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # set by Postgres on INSERT
        nullable=False,
    )


@event.listens_for(User, "before_insert")
def _ensure_user_normalized_email(mapper, connection, target) -> None:
    """Keep direct ORM/test inserts consistent with the non-null invariant."""

    if not target.normalized_email and target.email:
        target.normalized_email = str(target.email).strip().casefold()


class Thread(Base):
    __tablename__ = "thread"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    messages = relationship(
        "Message", back_populates="thread", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "message"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(
        UUID(as_uuid=True),
        ForeignKey("thread.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    role = Column(String, nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    thread = relationship("Thread", back_populates="messages")


class Document(Base):
    __tablename__ = "document"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    title = Column(String, nullable=False)  # uniqueness handled by explicit index
    content = Column(Text, nullable=True)

    # Audit fields
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Explicit index / unique constraint on title for fast look‑ups
    __table_args__ = (Index("ix_document_title", "title", unique=True),)


class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    doc_id: Mapped[str] = mapped_column(index=True)

    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)

    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)

    # We will create:
    # - content_tsv as GENERATED in SQL migration (tsvector)
    # - embedding as pgvector vector(dim)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CapabilityMetadata(Base):
    __tablename__ = "capability_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    capability_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    extra: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_capability_metadata_capability_tenant",
            "capability_id",
            "tenant_id",
            unique=True,
        ),
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    thread_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    status = Column(
        String, nullable=False, default="running"
    )  # running|paused|done|failed

    workflow = Column(JSONB, nullable=False)
    state = Column(JSONB, nullable=False)

    extra = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WorkflowRunEvent(Base):
    __tablename__ = "workflow_run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuntimeWorkflow(Base):
    __tablename__ = "runtime_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String, nullable=False)
    workflow = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_runtime_workflows_user_id_name", "user_id", "name"),)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    agent_run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    workflow_run_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    status = Column(String, nullable=False, default="running")
    state = Column(JSONB, nullable=False)
    usage = Column(JSONB, nullable=True)
    extra = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AgentRunEvent(Base):
    __tablename__ = "agent_run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.agent_run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequence = Column(Integer, nullable=False, index=True)
    event = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ObjectiveLearningExperienceRecord(Base):
    """
    Immutable extracted learning experience for one verified
    objective resolution.

    The record preserves one complete, versioned extraction
    snapshot. It is append-only and informational only. Durable
    storage does not activate planner guidance, alter ranking,
    authorize execution, bypass verification, or mutate runtime
    policy.
    """

    __tablename__ = "objective_learning_experiences"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "resolution_record_id",
            "schema_ref",
            "profile_ref",
            "profile_version",
            "extractor_ref",
            "extractor_version",
            name=("uq_objective_learning_experiences_semantic_extraction"),
        ),
        Index(
            "ix_objective_learning_experiences_owner_created",
            "user_id",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_objective_learning_experiences_objective_created",
            "user_id",
            "objective_namespace",
            "objective_type",
            "objective_ref",
            "created_at",
        ),
        Index(
            "ix_objective_learning_experiences_resolution_created",
            "resolution_record_id",
            "created_at",
        ),
        Index(
            "ix_objective_learning_experiences_profile_extractor",
            "profile_ref",
            "profile_version",
            "extractor_ref",
            "extractor_version",
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

    tenant_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    resolution_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "objective_resolution_records.id",
            name=("fk_objective_learning_experiences_resolution_record"),
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    objective_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    objective_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    objective_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    schema_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    profile_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    profile_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    extractor_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    extractor_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    outcome_ref: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    evaluation_ref: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    workflow_run_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    dimension_keys_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    evidence_refs_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    validity_scope_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    experience_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    informational_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    authorizes_execution: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


# Import domain models so Alembic can see them in migrations/env.py. Keeping
# registration at that composition boundary avoids circular worker imports.
class PlatformJob(Base):
    __tablename__ = "platform_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    job_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued",
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    locked_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    __table_args__ = (
        Index(
            "uq_platform_jobs_user_type_idempotency_key",
            "user_id",
            "job_type",
            "idempotency_key",
            unique=True,
            postgresql_where=(idempotency_key.is_not(None) & user_id.is_not(None)),
        ),
        Index(
            "uq_platform_jobs_global_type_idempotency_key",
            "job_type",
            "idempotency_key",
            unique=True,
            postgresql_where=(idempotency_key.is_not(None) & user_id.is_(None)),
        ),
    )


class WorkflowSchedule(Base):
    __tablename__ = "workflow_schedules"

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

    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    schedule_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    interval_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    cron_expression: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="UTC",
    )

    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    run_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_runs: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", index=True
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="accepted", index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PlatformEvent(Base):
    __tablename__ = "platform_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="published",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )


class CapabilityPerformanceObservationRecord(Base):
    """
    Durable projection of one provider attempt from a capability event.

    The immutable PlatformEvent remains the source of truth. This table is a
    queryable, replayable projection and must not directly mutate provider
    health or selection policy.
    """

    __tablename__ = "capability_performance_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    correlation_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    attempt_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    requested_capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    resolved_capability_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    succeeded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    duration_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    failure_kind: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    exception_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    fallback_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    fallback_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    health_probe: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    health_probe_lease_token: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    final_attempt: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    workflow_run_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    planner_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    thread_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    observation_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_event_id",
            "attempt_index",
            name=("uq_capability_performance_observation_event_attempt"),
        ),
        Index(
            "ix_cap_perf_capability_provider_created",
            "resolved_capability_id",
            "provider_id",
            "created_at",
        ),
        Index(
            "ix_cap_perf_tenant_capability_provider_created",
            "tenant_id",
            "resolved_capability_id",
            "provider_id",
            "created_at",
        ),
        Index(
            "ix_cap_perf_provider_failure_created",
            "provider_id",
            "failure_kind",
            "created_at",
        ),
        Index(
            "ix_cap_perf_health_scope_observed",
            "observed_at",
            "tenant_id",
            "resolved_capability_id",
            "provider_id",
            "provider_ref",
        ),
    )


class TaskVerificationRecord(Base):
    """
    Append-only durable record for one business-outcome verification attempt.

    verification_id groups retries for the same logical verification.
    attempt_number identifies one immutable attempt in that group.
    idempotency_key prevents duplicate delivery of the same attempt request.
    """

    __tablename__ = "task_verification_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    verification_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    workflow_run_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    outcome: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    reason_code: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    retryable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    inputs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    requested_outcome_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    execution_output_json: Mapped[Any] = mapped_column(
        JSONB,
        nullable=True,
    )

    observed_outcome_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    request_metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name=("uq_task_verification_user_idempotency"),
        ),
        UniqueConstraint(
            "user_id",
            "verification_id",
            "attempt_number",
            name=("uq_task_verification_user_verification_attempt"),
        ),
        Index(
            "ix_task_verification_owner_created",
            "user_id",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_task_verification_scope_outcome",
            "user_id",
            "tenant_id",
            "capability_id",
            "outcome",
            "created_at",
        ),
        Index(
            "ix_task_verification_correlation_created",
            "user_id",
            "correlation_id",
            "created_at",
        ),
        Index(
            "ix_task_verification_workflow_task",
            "user_id",
            "workflow_run_id",
            "task_id",
            "created_at",
        ),
    )


class CapabilityLearningObservationRecord(Base):
    """
    Immutable reusable evidence derived from a task-verification attempt.

    This projection is append-only and must not directly modify provider
    selection, health, traffic allocation, or runtime policy.
    """

    __tablename__ = "capability_learning_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "platform_events.id",
            name="fk_cap_learn_event",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    source_verification_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "task_verification_records.id",
            name="fk_cap_learn_verify_record",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    verification_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    reason_code: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    retryable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    is_final: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    workflow_run_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    observed_outcome_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    evidence_summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    context_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    observation_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_event_id",
            name="uq_cap_learn_source_event",
        ),
        UniqueConstraint(
            "source_verification_record_id",
            name="uq_cap_learn_verification_record",
        ),
        UniqueConstraint(
            "user_id",
            "verification_id",
            "attempt_number",
            name=("uq_cap_learning_user_verification_attempt"),
        ),
        Index(
            "ix_cap_learning_owner_observed",
            "user_id",
            "tenant_id",
            "observed_at",
        ),
        Index(
            "ix_cap_learning_scope_outcome",
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "action",
            "outcome",
            "observed_at",
        ),
        Index(
            "ix_cap_learning_final_scope",
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "is_final",
            "observed_at",
        ),
        Index(
            "ix_cap_learning_workflow_task",
            "user_id",
            "workflow_run_id",
            "task_id",
            "observed_at",
        ),
    )


class CapabilityProviderHealthStateRecord(Base):
    """
    Durable scoped provider-health state.

    This state is advisory until an explicit scoped resolver integration is
    introduced. It must not mutate the legacy global ProviderHealthRegistry.
    """

    __tablename__ = "capability_provider_health_states"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    scope_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        unique=True,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    current_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="healthy",
        index=True,
    )

    qualifying_recommendation: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    qualifying_windows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    probe_lease_token: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    probe_lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    probe_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    manual_override_state: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    manual_override_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    manual_override_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    __table_args__ = (
        Index(
            "ix_cap_health_state_user_scope",
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
        ),
        Index(
            "ix_cap_health_state_provider_status",
            "provider_id",
            "current_state",
            "updated_at",
        ),
    )


class CapabilityProviderHealthProbeResultRecord(Base):
    """
    Append-only result for one completed half-open provider probe.

    lease_token is globally unique, making repeated completion delivery
    idempotent independently of mutable health-state fields.
    """

    __tablename__ = "capability_provider_health_probe_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "capability_provider_health_states.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    lease_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    scope_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    succeeded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    previous_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    resulting_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    failure_kind: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CapabilityProviderHealthDecisionRecord(Base):
    """
    Append-only, idempotent history of scoped health evaluations.
    """

    __tablename__ = "capability_provider_health_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "capability_provider_health_states.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    decision_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        unique=True,
        index=True,
    )

    evaluation_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    previous_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    proposed_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    resulting_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    evidence_recommendation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    evidence_sufficient: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    qualifying_windows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    required_windows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    state_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_cap_health_decision_scope_time",
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "evaluated_at",
        ),
    )


class CapabilityProviderInstallationRecord(Base):
    """
    Secret-free projection of an owned provider installation.

    Credentials remain owned by the provider/domain integration. This record
    contains only availability and verification state used by semantic
    capability resolution.
    """

    __tablename__ = "capability_provider_installations"

    __table_args__ = (
        UniqueConstraint(
            "scope_key",
            name="uq_cap_provider_installation_scope",
        ),
        Index(
            "ix_cap_provider_installation_owner_provider",
            "user_id",
            "tenant_id",
            "provider_id",
        ),
        Index(
            "ix_cap_provider_installation_external_connection",
            "integration_kind",
            "integration_connection_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    scope_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    integration_kind: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    integration_connection_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    configuration_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unconfigured",
    )

    authentication_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="missing",
    )

    verification_state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unverified",
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ObjectiveLearningPolicyRevisionRecord(Base):
    """
    Append-only snapshot of one complete versioned objective-learning
    profile and qualification policy.

    Revisions remain informational and cannot authorize planning,
    provider selection, workflow behavior, runtime policy, or execution.
    """

    __tablename__ = "objective_learning_policy_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    scope_key: Mapped[str] = mapped_column(
        String(1500),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    objective_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    profile_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    profile_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    policy_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    policy_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    profile_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    informational_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    authorizes_execution: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "scope_key",
            "policy_version",
            name="uq_objective_learning_policy_scope_version",
        ),
        Index(
            "ix_objective_learning_policy_owner_scope_version",
            "user_id",
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "profile_ref",
            "policy_ref",
            "policy_version",
        ),
        Index(
            "ix_objective_learning_policy_owner_created",
            "user_id",
            "created_at",
        ),
    )


class ObjectiveLearningCandidateRevisionRecord(Base):
    """
    Append-only revision of one reviewable objective-learning
    candidate.

    Approval records human acceptance of advisory evidence only.
    These records do not alter ranking, planning, workflows,
    provider selection, runtime policy, verification, or execution.
    """

    __tablename__ = "objective_learning_candidate_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    objective_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    objective_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    schema_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    profile_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    profile_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    extractor_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    extractor_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    approval_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    validation_passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    scope_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    policy_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    policy_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    candidate_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    informational_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    authorizes_execution: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "candidate_id",
            "version",
            name=("uq_objective_learning_candidate_revision"),
        ),
        Index(
            "ix_objective_learning_candidate_owner_scope",
            "user_id",
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "created_at",
        ),
        Index(
            "ix_objective_learning_candidate_owner_status",
            "user_id",
            "status",
            "approval_status",
            "created_at",
        ),
        Index(
            "ix_objective_learning_candidate_fingerprint",
            "user_id",
            "scope_fingerprint",
            "created_at",
        ),
    )


class BusinessLearningInsightCandidateRevisionRecord(Base):
    """
    Append-only revision of a reviewable business-learning
    insight candidate.

    Approval records a human decision only. These records
    do not activate planning, workflows, routing, runtime
    policy, or business actions.
    """

    __tablename__ = "business_learning_insight_candidate_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    objective_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    decision: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    kind: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    approval_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    validation_passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    evidence_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    candidate_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "version",
            name=("uq_business_learning_candidate_id_version"),
        ),
        Index(
            "ix_business_learning_candidate_owner_created",
            "user_id",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_business_learning_candidate_owner_scope",
            "user_id",
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "decision",
            "created_at",
        ),
        Index(
            "ix_business_learning_candidate_owner_status",
            "user_id",
            "status",
            "approval_status",
            "created_at",
        ),
        Index(
            "ix_business_learning_candidate_fingerprint",
            "user_id",
            "evidence_fingerprint",
            "created_at",
        ),
    )


class CapabilityLearningInsightCandidateRevisionRecord(Base):
    """
    Append-only revision of a reviewable learning insight candidate.

    Revisions preserve proposal, validation, review, and promotion-eligibility
    history. These records are advisory and do not activate planner behavior,
    provider selection, traffic allocation, health, or runtime policy.
    """

    __tablename__ = "capability_learning_insight_candidate_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    kind: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    approval_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    promotion_target: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    validation_passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    promotion_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    evidence_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    candidate_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "version",
            name=("uq_cap_learning_candidate_id_version"),
        ),
        Index(
            "ix_cap_learning_candidate_owner_created",
            "user_id",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_cap_learning_candidate_owner_scope",
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "action",
            "created_at",
        ),
        Index(
            "ix_cap_learning_candidate_owner_status",
            "user_id",
            "status",
            "approval_status",
            "promotion_eligible",
            "created_at",
        ),
        Index(
            "ix_cap_learning_candidate_fingerprint",
            "user_id",
            "evidence_fingerprint",
            "created_at",
        ),
    )


class CapabilityLearningInsightPromotionRecord(Base):
    """
    Append-only event in an explicit learning-insight promotion lifecycle.

    Promotion events are advisory registry records and do not directly alter
    planner behavior, provider selection, allocation, health, or runtime
    policy.
    """

    __tablename__ = "capability_learning_insight_promotion_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    event_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    candidate_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    promotion_target: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    evidence_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    promotion_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "promotion_id",
            "event_version",
            name=("uq_cap_learning_promotion_event_version"),
        ),
        Index(
            "ix_cap_learning_promotion_owner_created",
            "user_id",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_cap_learning_promotion_candidate",
            "user_id",
            "candidate_id",
            "created_at",
        ),
        Index(
            "ix_cap_learning_promotion_owner_status",
            "user_id",
            "status",
            "promotion_target",
            "created_at",
        ),
        Index(
            "ix_cap_learning_promotion_scope",
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "action",
            "created_at",
        ),
    )


class CapabilityRuntimePolicyRevisionRecord(Base):
    """
    Append-only revision of a scoped capability runtime policy.

    Revisions are immutable. A new configuration change inserts version N+1
    for the same scope_key, preserving audit and rollback history.
    """

    __tablename__ = "capability_runtime_policy_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    policy_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="capability_runtime",
        index=True,
    )

    scope_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    capability_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    provider_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    policy_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "scope_key",
            "version",
            name=("uq_cap_runtime_policy_scope_version"),
        ),
        Index(
            "ix_cap_runtime_policy_owner_scope_version",
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "version",
        ),
        Index(
            "ix_cap_runtime_policy_provider_ref_version",
            "provider_ref",
            "version",
        ),
    )


class PlatformDeadLetter(Base):
    __tablename__ = "platform_dead_letters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    job_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="dead",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class WorkflowWait(Base):
    __tablename__ = "workflow_waits"

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

    workflow_run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    node_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    wait_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="waiting",
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    resolution: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    claimed_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class WorkflowRunSnapshot(Base):
    __tablename__ = "workflow_run_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    snapshot_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    node_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    event: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class WorkflowEvalDataset(Base):
    __tablename__ = "workflow_eval_datasets"

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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    domain: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
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

    cases: Mapped[list["WorkflowEvalCase"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class WorkflowEvalCase(Base):
    __tablename__ = "workflow_eval_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_eval_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    input_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    expected_output: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    expected_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    dataset: Mapped[WorkflowEvalDataset] = relationship(
        back_populates="cases",
    )


class WorkflowDeployment(Base):
    __tablename__ = "workflow_deployments"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow_key = mapped_column(String, nullable=False, index=True)

    workflow_version_id = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    environment = mapped_column(
        String,
        nullable=False,
        default="production",
        index=True,
    )

    deployed_by = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    metadata_json = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ObjectiveResolutionRecord(Base):
    """
    Immutable durable projection of one evaluated objective.

    The complete normalized assessment is retained in
    assessment_json. Indexed columns support objective history,
    unresolved-objective lookup, workflow tracing, and future
    repair orchestration.

    This generic record deliberately uses opaque source outcome
    and evaluation references rather than foreign keys to
    product-domain tables.
    """

    __tablename__ = "objective_resolution_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "platform_events.id",
            name="fk_objective_resolution_source_event",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    objective_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    objective_ref: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    objective_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source_outcome_ref: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    outcome_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source_evaluation_ref: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    evaluation_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    projection_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    assessment_schema_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    workflow_run_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    reason_code: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    is_terminal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    achieved_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unresolved_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    failed_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    pending_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unknown_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    not_executed_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    assessment_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_event_id",
            name="uq_objective_resolution_source_event",
        ),
        UniqueConstraint(
            "user_id",
            "objective_namespace",
            "source_evaluation_ref",
            "evaluation_version",
            "projection_version",
            name=("uq_objective_resolution_evaluation_projection"),
        ),
        Index(
            "ix_objective_resolution_owner_created",
            "user_id",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_objective_resolution_objective_history",
            "user_id",
            "objective_namespace",
            "objective_ref",
            "objective_version",
            "created_at",
        ),
        Index(
            "ix_objective_resolution_scope_status",
            "user_id",
            "objective_namespace",
            "objective_type",
            "status",
            "created_at",
        ),
        Index(
            "ix_objective_resolution_workflow_created",
            "user_id",
            "workflow_run_id",
            "created_at",
        ),
        Index(
            "ix_objective_resolution_terminal_created",
            "user_id",
            "is_terminal",
            "created_at",
        ),
    )


class ObjectiveRepairExecutionRecord(Base):
    """
    Immutable request and plan snapshot for one objective-repair
    attempt.

    Workflow launch fields are nullable because planning becomes
    durable before a product workflow is queued.
    """

    __tablename__ = "objective_repair_executions"
    __table_args__ = (
        UniqueConstraint(
            "source_event_id",
            name=("uq_objective_repair_executions_source_event"),
        ),
        UniqueConstraint(
            "user_id",
            "resolution_record_id",
            "repair_request_version",
            "planner_policy_version",
            "attempt_number",
            name=("uq_objective_repair_executions_semantic_attempt"),
        ),
        UniqueConstraint(
            "user_id",
            "repair_request_ref",
            "attempt_number",
            name=("uq_objective_repair_executions_request_attempt"),
        ),
        Index(
            "ix_objective_repair_executions_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_objective_repair_executions_user_objective_created",
            "user_id",
            "objective_namespace",
            "objective_type",
            "objective_ref",
            "created_at",
        ),
        Index(
            "ix_objective_repair_executions_resolution_attempt",
            "resolution_record_id",
            "attempt_number",
        ),
        Index(
            "ix_objective_repair_executions_user_status_created",
            "user_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_objective_repair_executions_workflow_job",
            "workflow_job_id",
        ),
        Index(
            "ix_objective_repair_executions_workflow_run",
            "workflow_run_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "platform_events.id",
            name=("fk_objective_repair_executions_source_event"),
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    resolution_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "objective_resolution_records.id",
            name=("fk_objective_repair_executions_resolution_record"),
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    objective_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    objective_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    objective_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    repair_request_ref: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    repair_request_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    repair_plan_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    planner_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    planner_policy_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    controlling_disposition: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="planned",
        index=True,
    )

    target_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    planned_target_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    deferred_target_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    unhandled_target_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    requires_human_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    automatic_execution_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    request_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    plan_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    workflow_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    workflow_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "platform_jobs.id",
            name=("fk_objective_repair_executions_workflow_job"),
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    workflow_run_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    launched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    result_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class BusinessLearningObservationRecord(Base):
    """
    Immutable normalized evidence about one evaluated
    business objective.

    This projection is append-only and descriptive. It
    must not directly mutate planning, workflow policy,
    routing, or runtime behavior.
    """

    __tablename__ = "business_learning_observations"

    __table_args__ = (
        UniqueConstraint(
            "source_event_id",
            name="uq_business_learning_source_event",
        ),
        UniqueConstraint(
            "source_evaluation_record_id",
            name=("uq_business_learning_source_evaluation"),
        ),
        Index(
            "ix_business_learning_owner_observed",
            "user_id",
            "tenant_id",
            "observed_at",
        ),
        Index(
            "ix_business_learning_objective_result",
            "user_id",
            "objective_namespace",
            "objective_type",
            "result",
            "observed_at",
        ),
        Index(
            "ix_business_learning_workflow",
            "user_id",
            "workflow_run_id",
            "observed_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "platform_events.id",
            name=("fk_business_learning_event"),
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_evaluation_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    source_outcome_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    objective_ref: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    objective_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    source_objective_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    outcome_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    evaluation_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    result: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    reason_code: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    retryable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    is_final: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    decision: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    outcome_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    achieved_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    failed_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    pending_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unknown_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    not_executed_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    workflow_run_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    conversation_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    chat_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    observed_outcome_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    evidence_summary_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    context_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    observation_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
