"""add customer service event subscriptions

Revision ID: 9a0ec515acfe
Revises: oc1a000000001
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9a0ec515acfe"
down_revision = "oc1a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_event_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=True),
        sa.Column("workflow_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workflow_template_id"], ["cs_workflow_templates.id"]),
        sa.UniqueConstraint("user_id", "event_type", "name", name="uq_cs_event_subscription_name"),
    )
    op.create_index("ix_cs_event_subscriptions_user_id", "cs_event_subscriptions", ["user_id"])
    op.create_index("ix_cs_event_subscriptions_event_type", "cs_event_subscriptions", ["event_type"])
    op.create_index("ix_cs_event_subscriptions_channel", "cs_event_subscriptions", ["channel"])
    op.create_index("ix_cs_event_subscriptions_workflow_template_id", "cs_event_subscriptions", ["workflow_template_id"])


def downgrade() -> None:
    op.drop_index("ix_cs_event_subscriptions_workflow_template_id", table_name="cs_event_subscriptions")
    op.drop_index("ix_cs_event_subscriptions_channel", table_name="cs_event_subscriptions")
    op.drop_index("ix_cs_event_subscriptions_event_type", table_name="cs_event_subscriptions")
    op.drop_index("ix_cs_event_subscriptions_user_id", table_name="cs_event_subscriptions")
    op.drop_table("cs_event_subscriptions")
