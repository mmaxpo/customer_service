"""job heartbeat and leasing

Revision ID: j2a000000001
Revises: dlq1a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j2a000000001"
down_revision: Union[str, Sequence[str], None] = "dlq1a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_jobs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_jobs", "heartbeat_at")
