"""Add proactive customer-service playbooks.

Revision ID: cap041
Revises: cap040
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap041"
down_revision = "cap040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_proactive_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("signal", sa.String(length=80), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("lookback_hours", sa.Integer(), nullable=False),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False),
        sa.Column("action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "signal", name="uq_cs_proactive_policy_workspace_signal"),
    )
    op.create_index("ix_cs_proactive_policies_workspace_id", "cs_proactive_policies", ["workspace_id"])
    op.create_table(
        "cs_proactive_incidents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("policy_id", sa.UUID(), nullable=False),
        sa.Column("signal", sa.String(length=80), nullable=False),
        sa.Column("fingerprint", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("conversation_id", sa.UUID()),
        sa.Column("customer_id", sa.UUID()),
        sa.Column("provider_id", sa.String(length=255)),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_taken", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["cs_proactive_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["cs_conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["cs_customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "fingerprint", name="uq_cs_proactive_incident_fingerprint"),
    )
    op.create_index("ix_cs_proactive_incidents_workspace_id", "cs_proactive_incidents", ["workspace_id"])
    op.create_index("ix_cs_proactive_incidents_signal", "cs_proactive_incidents", ["signal"])
    op.create_index("ix_cs_proactive_incidents_conversation_id", "cs_proactive_incidents", ["conversation_id"])
    op.create_index("ix_cs_proactive_incidents_customer_id", "cs_proactive_incidents", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_cs_proactive_incidents_customer_id", table_name="cs_proactive_incidents")
    op.drop_index("ix_cs_proactive_incidents_conversation_id", table_name="cs_proactive_incidents")
    op.drop_index("ix_cs_proactive_incidents_signal", table_name="cs_proactive_incidents")
    op.drop_index("ix_cs_proactive_incidents_workspace_id", table_name="cs_proactive_incidents")
    op.drop_table("cs_proactive_incidents")
    op.drop_index("ix_cs_proactive_policies_workspace_id", table_name="cs_proactive_policies")
    op.drop_table("cs_proactive_policies")
