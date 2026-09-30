"""workflow metrics

Revision ID: wm1a000000001
Revises: wv1a000000001
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "wm1a000000001"
down_revision: Union[str, Sequence[str], None] = "wv1a000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_run_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_definition_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("node_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approval_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_workflow_run_metrics_user_id", "workflow_run_metrics", ["user_id"])
    op.create_index("ix_workflow_run_metrics_workflow_run_id", "workflow_run_metrics", ["workflow_run_id"])
    op.create_index("ix_workflow_run_metrics_definition_version", "workflow_run_metrics", ["workflow_definition_id", "workflow_version"])
    op.create_index("ix_workflow_run_metrics_status", "workflow_run_metrics", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_run_metrics_status", table_name="workflow_run_metrics")
    op.drop_index("ix_workflow_run_metrics_definition_version", table_name="workflow_run_metrics")
    op.drop_index("ix_workflow_run_metrics_workflow_run_id", table_name="workflow_run_metrics")
    op.drop_index("ix_workflow_run_metrics_user_id", table_name="workflow_run_metrics")
    op.drop_table("workflow_run_metrics")
