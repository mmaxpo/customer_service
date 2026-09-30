"""add runtime workflow persistence tables

Revision ID: 4f2b7c945184
Revises: 3d8edd771e53
Create Date: 2026-02-17 19:35:26.359282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4f2b7c945184"
down_revision: Union[str, Sequence[str], None] = "3d8edd771e53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- workflow_runs ---
    op.create_table(
        "workflow_runs",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("thread_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("workflow", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("ix_workflow_runs_user_id"), "workflow_runs", ["user_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_thread_id"), "workflow_runs", ["thread_id"], unique=False)

    # --- workflow_run_events ---
    op.create_table(
        "workflow_run_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("event", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_run_events_run_id"), "workflow_run_events", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_run_events_run_id"), table_name="workflow_run_events")
    op.drop_table("workflow_run_events")

    op.drop_index(op.f("ix_workflow_runs_thread_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_user_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")