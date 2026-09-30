"""Add merchant autopilot policies and structured intelligence metadata.

Revision ID: cap039
Revises: cap038
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap039"
down_revision = "cap038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_autopilot_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("intent", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("minimum_confidence", sa.Float(), nullable=False),
        sa.Column("maximum_auto_risk", sa.String(length=16), nullable=False),
        sa.Column(
            "allowed_channels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "allowed_languages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("mutation_requires_approval", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "intent",
            name="uq_cs_autopilot_policy_workspace_intent",
        ),
    )
    op.create_index(
        "ix_cs_autopilot_policies_workspace_id",
        "cs_autopilot_policies",
        ["workspace_id"],
    )
    op.add_column(
        "cs_conversation_insights",
        sa.Column("language", sa.String(length=16), nullable=False, server_default="und"),
    )
    op.add_column(
        "cs_conversation_insights",
        sa.Column("model_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "cs_conversation_insights",
        sa.Column("fallback_reason", sa.String(length=255), nullable=True),
    )
    op.alter_column("cs_conversation_insights", "language", server_default=None)


def downgrade() -> None:
    op.drop_column("cs_conversation_insights", "fallback_reason")
    op.drop_column("cs_conversation_insights", "model_version")
    op.drop_column("cs_conversation_insights", "language")
    op.drop_index(
        "ix_cs_autopilot_policies_workspace_id",
        table_name="cs_autopilot_policies",
    )
    op.drop_table("cs_autopilot_policies")
