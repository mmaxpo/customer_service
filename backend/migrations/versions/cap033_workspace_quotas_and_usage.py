"""Add workspace quotas and cost-observability ledger.

Revision ID: cap033
Revises: cap032
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "cap033"
down_revision = "cap032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_quotas",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "monthly_token_limit",
            sa.BigInteger(),
            nullable=False,
            server_default="1000000",
        ),
        sa.Column(
            "monthly_cost_microusd_limit",
            sa.BigInteger(),
            nullable=False,
            server_default="50000000",
        ),
        sa.Column(
            "per_run_token_limit",
            sa.Integer(),
            nullable=False,
            server_default="20000",
        ),
        sa.Column(
            "per_run_llm_call_limit",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
        sa.Column(
            "per_run_tool_call_limit",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
        sa.Column(
            "concurrent_run_limit",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("workspace_id"),
    )
    op.execute(
        """
        INSERT INTO workspace_quotas (workspace_id)
        SELECT id FROM workspaces
        ON CONFLICT (workspace_id) DO NOTHING
        """
    )

    op.create_table(
        "workspace_usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "estimated_cost_microusd",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("rejection_reason", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_workspace_usage_events_workspace_id",
        "workspace_usage_events",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_usage_events_workspace_created",
        "workspace_usage_events",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("workspace_usage_events")
    op.drop_table("workspace_quotas")
