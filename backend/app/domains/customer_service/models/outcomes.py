from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.models import Base


class CustomerSupportOutcomeRecord(Base):
    """Canonical immutable business outcome for one support review plan."""

    __tablename__ = "cs_support_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "review_plan_id",
            name="uq_cs_support_outcomes_user_review_plan",
        ),
        Index(
            "ix_cs_support_outcomes_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_cs_support_outcomes_user_conversation_created",
            "user_id",
            "conversation_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    review_plan_id: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    objective_namespace: Mapped[str] = mapped_column(
        String(100), nullable=False, default="customer_service.support"
    )
    objective_ref: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    source_objective_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    outcome_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    objective_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    order_ref: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    operation_count: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    customer_message: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    operations_json: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    outcome_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )

    recording_idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CustomerSupportOutcomeEvaluationRecord(Base):
    """
    Immutable deterministic evaluation of one canonical support outcome.

    evaluation_version allows evaluation rules to evolve without rewriting
    historical conclusions.
    """

    __tablename__ = "cs_support_outcome_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "support_outcome_id",
            "evaluation_version",
            name=(
                "uq_cs_support_outcome_eval_"
                "user_outcome_version"
            ),
        ),
        Index(
            "ix_cs_support_outcome_eval_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_cs_support_outcome_eval_user_result_created",
            "user_id",
            "result",
            "created_at",
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

    support_outcome_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "cs_support_outcomes.id",
            name="fk_cs_support_outcome_eval_outcome",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    review_plan_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    evaluation_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
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
        nullable=False,
        default=False,
        index=True,
    )

    achieved_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    failed_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    pending_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    unknown_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    not_executed_operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    observed_outcome_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    evidence_json: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
