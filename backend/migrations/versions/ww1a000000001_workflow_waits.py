"""workflow waits foundation

Revision ID: ww1a000000001
Revises: j2a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ww1a000000001"
down_revision: Union[str, Sequence[str], None] = "j2a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_waits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=255), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("wait_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="waiting"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resolution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_workflow_waits_user_id", "workflow_waits", ["user_id"])
    op.create_index("ix_workflow_waits_workflow_run_id", "workflow_waits", ["workflow_run_id"])
    op.create_index("ix_workflow_waits_node_id", "workflow_waits", ["node_id"])
    op.create_index("ix_workflow_waits_wait_type", "workflow_waits", ["wait_type"])
    op.create_index("ix_workflow_waits_status", "workflow_waits", ["status"])
    op.create_index("ix_workflow_waits_expires_at", "workflow_waits", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_waits_expires_at", table_name="workflow_waits")
    op.drop_index("ix_workflow_waits_status", table_name="workflow_waits")
    op.drop_index("ix_workflow_waits_wait_type", table_name="workflow_waits")
    op.drop_index("ix_workflow_waits_node_id", table_name="workflow_waits")
    op.drop_index("ix_workflow_waits_workflow_run_id", table_name="workflow_waits")
    op.drop_index("ix_workflow_waits_user_id", table_name="workflow_waits")
    op.drop_table("workflow_waits")
