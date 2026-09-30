"""platform dead letters

Revision ID: dlq1a000000001
Revises: e1a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "dlq1a000000001"
down_revision: Union[str, Sequence[str], None] = "e1a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_dead_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="dead"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_platform_dead_letters_job_id", "platform_dead_letters", ["job_id"])
    op.create_index("ix_platform_dead_letters_user_id", "platform_dead_letters", ["user_id"])
    op.create_index("ix_platform_dead_letters_job_type", "platform_dead_letters", ["job_type"])
    op.create_index("ix_platform_dead_letters_status", "platform_dead_letters", ["status"])


def downgrade() -> None:
    op.drop_index("ix_platform_dead_letters_status", table_name="platform_dead_letters")
    op.drop_index("ix_platform_dead_letters_job_type", table_name="platform_dead_letters")
    op.drop_index("ix_platform_dead_letters_user_id", table_name="platform_dead_letters")
    op.drop_index("ix_platform_dead_letters_job_id", table_name="platform_dead_letters")
    op.drop_table("platform_dead_letters")
