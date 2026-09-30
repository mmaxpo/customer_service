"""add durable task verification records

Revision ID: cap011
Revises: cap010
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap011"
down_revision = "cap010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_verification_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "verification_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=500),
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
            "capability_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_ref",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "correlation_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "workflow_run_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "task_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "method",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "reason_code",
            sa.String(length=255),
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
            "inputs_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "requested_outcome_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "execution_output_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "observed_outcome_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "request_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name=(
                "uq_task_verification_user_"
                "idempotency"
            ),
        ),
        sa.UniqueConstraint(
            "user_id",
            "verification_id",
            "attempt_number",
            name=(
                "uq_task_verification_user_"
                "verification_attempt"
            ),
        ),
    )

    indexed_columns = (
        "verification_id",
        "user_id",
        "tenant_id",
        "capability_id",
        "provider_id",
        "provider_ref",
        "action",
        "correlation_id",
        "workflow_run_id",
        "task_id",
        "outcome",
        "method",
        "reason_code",
        "retryable",
        "completed_at",
        "created_at",
    )

    for column in indexed_columns:
        op.create_index(
            (
                "ix_task_verification_records_"
                f"{column}"
            ),
            "task_verification_records",
            [column],
            unique=False,
        )

    op.create_index(
        "ix_task_verification_owner_created",
        "task_verification_records",
        [
            "user_id",
            "tenant_id",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_task_verification_scope_outcome",
        "task_verification_records",
        [
            "user_id",
            "tenant_id",
            "capability_id",
            "outcome",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_task_verification_correlation_created",
        "task_verification_records",
        [
            "user_id",
            "correlation_id",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_task_verification_workflow_task",
        "task_verification_records",
        [
            "user_id",
            "workflow_run_id",
            "task_id",
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_verification_workflow_task",
        table_name="task_verification_records",
    )
    op.drop_index(
        "ix_task_verification_correlation_created",
        table_name="task_verification_records",
    )
    op.drop_index(
        "ix_task_verification_scope_outcome",
        table_name="task_verification_records",
    )
    op.drop_index(
        "ix_task_verification_owner_created",
        table_name="task_verification_records",
    )

    indexed_columns = (
        "created_at",
        "completed_at",
        "retryable",
        "reason_code",
        "method",
        "outcome",
        "task_id",
        "workflow_run_id",
        "correlation_id",
        "action",
        "provider_ref",
        "provider_id",
        "capability_id",
        "tenant_id",
        "user_id",
        "verification_id",
    )

    for column in indexed_columns:
        op.drop_index(
            (
                "ix_task_verification_records_"
                f"{column}"
            ),
            table_name=(
                "task_verification_records"
            ),
        )

    op.drop_table(
        "task_verification_records"
    )
