"""add objective resolution records

Revision ID: cap021
Revises: cap020
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap021"
down_revision = "cap020"
branch_labels = None
depends_on = None


TABLE = "objective_resolution_records"


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
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "objective_type",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "objective_ref",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "objective_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "source_outcome_ref",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "outcome_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "source_evaluation_ref",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "evaluation_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "projection_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "assessment_schema_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "workflow_run_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=100),
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
            "is_terminal",
            sa.Boolean(),
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
            "unresolved_operation_count",
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
            "assessment_json",
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
            name=(
                "fk_objective_resolution_source_event"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_event_id",
            name=(
                "uq_objective_resolution_source_event"
            ),
        ),
        sa.UniqueConstraint(
            "user_id",
            "objective_namespace",
            "source_evaluation_ref",
            "evaluation_version",
            "projection_version",
            name=(
                "uq_objective_resolution_"
                "evaluation_projection"
            ),
        ),
    )

    single_indexes = {
        "user_id": (
            "ix_objective_resolution_records_user_id"
        ),
        "tenant_id": (
            "ix_objective_resolution_records_tenant_id"
        ),
        "objective_namespace": (
            "ix_objective_resolution_records_"
            "objective_namespace"
        ),
        "objective_type": (
            "ix_objective_resolution_records_"
            "objective_type"
        ),
        "objective_ref": (
            "ix_objective_resolution_records_"
            "objective_ref"
        ),
        "source_outcome_ref": (
            "ix_objective_resolution_records_"
            "source_outcome_ref"
        ),
        "source_evaluation_ref": (
            "ix_objective_resolution_records_"
            "source_evaluation_ref"
        ),
        "workflow_run_id": (
            "ix_objective_resolution_records_"
            "workflow_run_id"
        ),
        "status": (
            "ix_objective_resolution_records_status"
        ),
        "reason_code": (
            "ix_objective_resolution_records_"
            "reason_code"
        ),
        "is_terminal": (
            "ix_objective_resolution_records_"
            "is_terminal"
        ),
        "created_at": (
            "ix_objective_resolution_records_created_at"
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
        "ix_objective_resolution_owner_created",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_objective_resolution_objective_history",
        TABLE,
        [
            "user_id",
            "objective_namespace",
            "objective_ref",
            "objective_version",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_objective_resolution_scope_status",
        TABLE,
        [
            "user_id",
            "objective_namespace",
            "objective_type",
            "status",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_objective_resolution_workflow_created",
        TABLE,
        [
            "user_id",
            "workflow_run_id",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_objective_resolution_terminal_created",
        TABLE,
        [
            "user_id",
            "is_terminal",
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table(TABLE)
