"""add customer support outcome evaluations

Revision ID: cap018
Revises: cap017
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap018"
down_revision = "cap017"
branch_labels = None
depends_on = None


TABLE = "cs_support_outcome_evaluations"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "support_outcome_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "review_plan_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
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
            "observed_outcome_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "evidence_json",
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
            ["support_outcome_id"],
            ["cs_support_outcomes.id"],
            name=(
                "fk_cs_support_outcome_eval_"
                "outcome"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "support_outcome_id",
            "evaluation_version",
            name=(
                "uq_cs_support_outcome_eval_"
                "user_outcome_version"
            ),
        ),
    )

    indexes = [
        (
            "ix_cs_support_outcome_"
            "evaluations_user_id",
            ["user_id"],
        ),
        (
            "ix_cs_support_outcome_"
            "evaluations_support_outcome_id",
            ["support_outcome_id"],
        ),
        (
            "ix_cs_support_outcome_"
            "evaluations_review_plan_id",
            ["review_plan_id"],
        ),
        (
            "ix_cs_support_outcome_"
            "evaluations_workflow_run_id",
            ["workflow_run_id"],
        ),
        (
            "ix_cs_support_outcome_"
            "evaluations_result",
            ["result"],
        ),
        (
            "ix_cs_support_outcome_"
            "evaluations_reason_code",
            ["reason_code"],
        ),
        (
            "ix_cs_support_outcome_"
            "evaluations_retryable",
            ["retryable"],
        ),
        (
            "ix_cs_support_outcome_eval_"
            "user_created",
            ["user_id", "created_at"],
        ),
        (
            "ix_cs_support_outcome_eval_"
            "user_result_created",
            [
                "user_id",
                "result",
                "created_at",
            ],
        ),
    ]

    for name, columns in indexes:
        op.create_index(
            name,
            TABLE,
            columns,
            unique=False,
        )


def downgrade() -> None:
    op.drop_table(TABLE)
