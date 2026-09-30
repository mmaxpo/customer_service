"""add business learning observations

Revision ID: cap019
Revises: cap018
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap019"
down_revision = "cap018"
branch_labels = None
depends_on = None


TABLE = "business_learning_observations"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_evaluation_record_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_outcome_record_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "objective_namespace",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "objective_ref",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "objective_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "source_objective_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "outcome_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "evaluation_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "result",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "reason_code",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "retryable",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "is_final",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "outcome_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "operation_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "achieved_operation_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "failed_operation_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "pending_operation_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "unknown_operation_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "not_executed_operation_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "workflow_run_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "chat_session_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "observed_outcome_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "evidence_summary_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "context_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "observation_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["platform_events.id"],
            name="fk_business_learning_event",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_event_id",
            name=(
                "uq_business_learning_source_event"
            ),
        ),
        sa.UniqueConstraint(
            "source_evaluation_record_id",
            name=(
                "uq_business_learning_"
                "source_evaluation"
            ),
        ),
    )

    single_indexes = {
        "source_event_id": (
            "ix_business_learning_source_event"
        ),
        "source_evaluation_record_id": (
            "ix_business_learning_source_eval"
        ),
        "source_outcome_record_id": (
            "ix_business_learning_source_outcome"
        ),
        "user_id": "ix_business_learning_user",
        "tenant_id": (
            "ix_business_learning_tenant"
        ),
        "objective_namespace": (
            "ix_business_learning_namespace"
        ),
        "objective_ref": (
            "ix_business_learning_objective_ref"
        ),
        "objective_type": (
            "ix_business_learning_objective_type"
        ),
        "result": "ix_business_learning_result",
        "reason_code": (
            "ix_business_learning_reason"
        ),
        "retryable": (
            "ix_business_learning_retryable"
        ),
        "is_final": (
            "ix_business_learning_final"
        ),
        "decision": (
            "ix_business_learning_decision"
        ),
        "outcome_status": (
            "ix_business_learning_status"
        ),
        "workflow_run_id": (
            "ix_business_learning_workflow_id"
        ),
        "conversation_id": (
            "ix_business_learning_conversation"
        ),
        "chat_session_id": (
            "ix_business_learning_chat_session"
        ),
        "observed_at": (
            "ix_business_learning_observed"
        ),
        "created_at": (
            "ix_business_learning_created"
        ),
    }

    for column, name in single_indexes.items():
        op.create_index(
            name,
            TABLE,
            [column],
            unique=False,
        )

    op.create_index(
        "ix_business_learning_owner_observed",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "observed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_business_learning_objective_result",
        TABLE,
        [
            "user_id",
            "objective_namespace",
            "objective_type",
            "result",
            "observed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_business_learning_workflow",
        TABLE,
        [
            "user_id",
            "workflow_run_id",
            "observed_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table(TABLE)
