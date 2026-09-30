"""platform jobs foundation

Revision ID: j1a000000001
Revises: cdc0c6cc16a6
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "j1a000000001"
down_revision: Union[str, Sequence[str], None] = "cdc0c6cc16a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_platform_jobs_user_id", "platform_jobs", ["user_id"])
    op.create_index("ix_platform_jobs_job_type", "platform_jobs", ["job_type"])
    op.create_index("ix_platform_jobs_status", "platform_jobs", ["status"])
    op.create_index("ix_platform_jobs_run_after", "platform_jobs", ["run_after"])


def downgrade() -> None:
    op.drop_index("ix_platform_jobs_run_after", table_name="platform_jobs")
    op.drop_index("ix_platform_jobs_status", table_name="platform_jobs")
    op.drop_index("ix_platform_jobs_job_type", table_name="platform_jobs")
    op.drop_index("ix_platform_jobs_user_id", table_name="platform_jobs")
    op.drop_table("platform_jobs")
