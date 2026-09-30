"""add customer service teams

Revision ID: 9e4258772a35
Revises: e308ef27dad6
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9e4258772a35"
down_revision = "e308ef27dad6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "name", name="uq_cs_team_name"),
    )
    op.create_index("ix_cs_teams_user_id", "cs_teams", ["user_id"])
    op.create_index("ix_cs_teams_is_active", "cs_teams", ["is_active"])

    op.create_table(
        "cs_team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["team_id"], ["cs_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["cs_agents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("team_id", "agent_id", name="uq_cs_team_member"),
    )
    op.create_index("ix_cs_team_members_user_id", "cs_team_members", ["user_id"])
    op.create_index("ix_cs_team_members_team_id", "cs_team_members", ["team_id"])
    op.create_index("ix_cs_team_members_agent_id", "cs_team_members", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_cs_team_members_agent_id", table_name="cs_team_members")
    op.drop_index("ix_cs_team_members_team_id", table_name="cs_team_members")
    op.drop_index("ix_cs_team_members_user_id", table_name="cs_team_members")
    op.drop_table("cs_team_members")

    op.drop_index("ix_cs_teams_is_active", table_name="cs_teams")
    op.drop_index("ix_cs_teams_user_id", table_name="cs_teams")
    op.drop_table("cs_teams")
