"""add customer service agents

Revision ID: e308ef27dad6
Revises: e8f6a21770c2
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e308ef27dad6"
down_revision = "e8f6a21770c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("availability", sa.String(length=50), nullable=False, server_default="available"),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("max_open_tickets", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "agent_user_id", name="uq_cs_agent_user"),
    )

    op.create_index("ix_cs_agents_user_id", "cs_agents", ["user_id"])
    op.create_index("ix_cs_agents_agent_user_id", "cs_agents", ["agent_user_id"])
    op.create_index("ix_cs_agents_email", "cs_agents", ["email"])
    op.create_index("ix_cs_agents_status", "cs_agents", ["status"])
    op.create_index("ix_cs_agents_availability", "cs_agents", ["availability"])


def downgrade() -> None:
    op.drop_index("ix_cs_agents_availability", table_name="cs_agents")
    op.drop_index("ix_cs_agents_status", table_name="cs_agents")
    op.drop_index("ix_cs_agents_email", table_name="cs_agents")
    op.drop_index("ix_cs_agents_agent_user_id", table_name="cs_agents")
    op.drop_index("ix_cs_agents_user_id", table_name="cs_agents")
    op.drop_table("cs_agents")
