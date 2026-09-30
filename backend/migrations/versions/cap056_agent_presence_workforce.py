"""add agent presence, schedules and time off

Revision ID: cap056
Revises: cap055
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cap056"
down_revision = "cap055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cs_agents", sa.Column("availability_source", sa.String(20), nullable=False, server_default="manual"))
    op.add_column("cs_agents", sa.Column("availability_mode", sa.String(20), nullable=False, server_default="manual"))
    op.add_column("cs_agents", sa.Column("last_presence_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cs_agents", sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cs_agents", sa.Column("schedule_timezone", sa.String(64), nullable=True))
    op.add_column("cs_agents", sa.Column("weekly_schedule", postgresql.JSONB(), nullable=True))
    op.create_index("ix_cs_agents_availability_mode", "cs_agents", ["availability_mode"])
    op.create_table(
        "cs_agent_time_off",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cs_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "agent_id", "starts_at", "ends_at", name="uq_cs_agent_time_off_range"),
    )
    op.create_index("ix_cs_agent_time_off_workspace_id", "cs_agent_time_off", ["workspace_id"])
    op.create_index("ix_cs_agent_time_off_agent_id", "cs_agent_time_off", ["agent_id"])
    op.create_index("ix_cs_agent_time_off_starts_at", "cs_agent_time_off", ["starts_at"])
    op.create_index("ix_cs_agent_time_off_ends_at", "cs_agent_time_off", ["ends_at"])


def downgrade() -> None:
    op.drop_table("cs_agent_time_off")
    op.drop_index("ix_cs_agents_availability_mode", table_name="cs_agents")
    for name in ("weekly_schedule", "schedule_timezone", "last_activity_at", "last_presence_at", "availability_mode", "availability_source"):
        op.drop_column("cs_agents", name)
