"""add customer service queues

Revision ID: 435a6f069a11
Revises: a2437a105fc7
Create Date: 2026-05-29 13:18:02.318668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '435a6f069a11'
down_revision: Union[str, Sequence[str], None] = 'a2437a105fc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "cs_queues",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),

        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("name", sa.String(length=255), nullable=False),

        sa.Column("description", sa.Text(), nullable=True),

        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column("channel", sa.String(length=64), nullable=True),

        sa.Column("intent", sa.String(length=100), nullable=True),

        sa.Column("priority", sa.String(length=50), nullable=True),

        sa.Column("priority_rank", sa.Integer(), nullable=False, server_default="100"),

        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),

        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.ForeignKeyConstraint(["team_id"], ["cs_teams.id"]),

        sa.UniqueConstraint("user_id", "name", name="uq_cs_queue_name"),

    )

    op.create_index("ix_cs_queues_user_id", "cs_queues", ["user_id"])

    op.create_index("ix_cs_queues_team_id", "cs_queues", ["team_id"])

    op.create_index("ix_cs_queues_channel", "cs_queues", ["channel"])

    op.create_index("ix_cs_queues_intent", "cs_queues", ["intent"])

    op.create_index("ix_cs_queues_priority", "cs_queues", ["priority"])

    op.create_index("ix_cs_queues_priority_rank", "cs_queues", ["priority_rank"])

    op.create_index("ix_cs_queues_is_default", "cs_queues", ["is_default"])

    op.create_index("ix_cs_queues_is_active", "cs_queues", ["is_active"])

def downgrade() -> None:

    op.drop_index("ix_cs_queues_is_active", table_name="cs_queues")

    op.drop_index("ix_cs_queues_is_default", table_name="cs_queues")

    op.drop_index("ix_cs_queues_priority_rank", table_name="cs_queues")

    op.drop_index("ix_cs_queues_priority", table_name="cs_queues")

    op.drop_index("ix_cs_queues_intent", table_name="cs_queues")

    op.drop_index("ix_cs_queues_channel", table_name="cs_queues")

    op.drop_index("ix_cs_queues_team_id", table_name="cs_queues")

    op.drop_index("ix_cs_queues_user_id", table_name="cs_queues")

    op.drop_table("cs_queues")
