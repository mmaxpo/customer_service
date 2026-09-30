"""workflow schedules foundation

Revision ID: s1a000000001
Revises: j1a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s1a000000001"
down_revision: Union[str, Sequence[str], None] = "j1a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("schedule_type", sa.String(length=50), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(length=100), nullable=False, server_default="UTC"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_runs", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_workflow_schedules_user_id", "workflow_schedules", ["user_id"])
    op.create_index("ix_workflow_schedules_workflow_id", "workflow_schedules", ["workflow_id"])
    op.create_index("ix_workflow_schedules_schedule_type", "workflow_schedules", ["schedule_type"])
    op.create_index("ix_workflow_schedules_status", "workflow_schedules", ["status"])
    op.create_index("ix_workflow_schedules_next_run_at", "workflow_schedules", ["next_run_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_schedules_next_run_at", table_name="workflow_schedules")
    op.drop_index("ix_workflow_schedules_status", table_name="workflow_schedules")
    op.drop_index("ix_workflow_schedules_schedule_type", table_name="workflow_schedules")
    op.drop_index("ix_workflow_schedules_workflow_id", table_name="workflow_schedules")
    op.drop_index("ix_workflow_schedules_user_id", table_name="workflow_schedules")
    op.drop_table("workflow_schedules")
