"""platform events foundation

Revision ID: e1a000000001
Revises: w1a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1a000000001"
down_revision: Union[str, Sequence[str], None] = "w1a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_platform_events_user_id", "platform_events", ["user_id"])
    op.create_index("ix_platform_events_event_type", "platform_events", ["event_type"])
    op.create_index("ix_platform_events_source", "platform_events", ["source"])
    op.create_index("ix_platform_events_status", "platform_events", ["status"])
    op.create_index("ix_platform_events_created_at", "platform_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_platform_events_created_at", table_name="platform_events")
    op.drop_index("ix_platform_events_status", table_name="platform_events")
    op.drop_index("ix_platform_events_source", table_name="platform_events")
    op.drop_index("ix_platform_events_event_type", table_name="platform_events")
    op.drop_index("ix_platform_events_user_id", table_name="platform_events")
    op.drop_table("platform_events")
