"""workflow run snapshots

Revision ID: ws1a000000001
Revises: ww2a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ws1a000000001"
down_revision: Union[str, Sequence[str], None] = "ww2a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_run_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_type", sa.String(length=100), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("node_type", sa.String(length=255), nullable=True),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("event", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_workflow_run_snapshots_workflow_run_id", "workflow_run_snapshots", ["workflow_run_id"])
    op.create_index("ix_workflow_run_snapshots_user_id", "workflow_run_snapshots", ["user_id"])
    op.create_index("ix_workflow_run_snapshots_snapshot_type", "workflow_run_snapshots", ["snapshot_type"])
    op.create_index("ix_workflow_run_snapshots_node_id", "workflow_run_snapshots", ["node_id"])
    op.create_index("ix_workflow_run_snapshots_seq", "workflow_run_snapshots", ["seq"])
    op.create_index("ix_workflow_run_snapshots_created_at", "workflow_run_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_run_snapshots_created_at", table_name="workflow_run_snapshots")
    op.drop_index("ix_workflow_run_snapshots_seq", table_name="workflow_run_snapshots")
    op.drop_index("ix_workflow_run_snapshots_node_id", table_name="workflow_run_snapshots")
    op.drop_index("ix_workflow_run_snapshots_snapshot_type", table_name="workflow_run_snapshots")
    op.drop_index("ix_workflow_run_snapshots_user_id", table_name="workflow_run_snapshots")
    op.drop_index("ix_workflow_run_snapshots_workflow_run_id", table_name="workflow_run_snapshots")
    op.drop_table("workflow_run_snapshots")
