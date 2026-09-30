"""add agent runtime persistence

Revision ID: 078f803aed08
Revises: d73c881c0999
Create Date: 2026-05-10 16:58:16.055514

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '078f803aed08'
down_revision: Union[str, Sequence[str], None] = 'd73c881c0999'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "agent_runs",

        sa.Column("run_id", sa.UUID(), nullable=False),

        sa.Column("user_id", sa.UUID(), nullable=True),

        sa.Column("workflow_run_id", sa.UUID(), nullable=True),

        sa.Column("status", sa.String(), nullable=False),

        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.Column("usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

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

        sa.PrimaryKeyConstraint("run_id"),

    )

    op.create_index(

        op.f("ix_agent_runs_user_id"),

        "agent_runs",

        ["user_id"],

        unique=False,

    )

    op.create_index(

        op.f("ix_agent_runs_workflow_run_id"),

        "agent_runs",

        ["workflow_run_id"],

        unique=False,

    )

    op.create_table(

        "agent_run_events",

        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),

        sa.Column("run_id", sa.UUID(), nullable=False),

        sa.Column("sequence", sa.Integer(), nullable=False),

        sa.Column("event", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.Column(

            "created_at",

            sa.DateTime(timezone=True),

            server_default=sa.text("now()"),

            nullable=False,

        ),

        sa.ForeignKeyConstraint(

            ["run_id"],

            ["agent_runs.run_id"],

            ondelete="CASCADE",

        ),

        sa.PrimaryKeyConstraint("id"),

    )

    op.create_index(

        op.f("ix_agent_run_events_run_id"),

        "agent_run_events",

        ["run_id"],

        unique=False,

    )

    op.create_index(

        op.f("ix_agent_run_events_sequence"),

        "agent_run_events",

        ["sequence"],

        unique=False,

    )

def downgrade() -> None:

    op.drop_index(op.f("ix_agent_run_events_sequence"), table_name="agent_run_events")

    op.drop_index(op.f("ix_agent_run_events_run_id"), table_name="agent_run_events")

    op.drop_table("agent_run_events")

    op.drop_index(op.f("ix_agent_runs_workflow_run_id"), table_name="agent_runs")

    op.drop_index(op.f("ix_agent_runs_user_id"), table_name="agent_runs")

    op.drop_table("agent_runs")
