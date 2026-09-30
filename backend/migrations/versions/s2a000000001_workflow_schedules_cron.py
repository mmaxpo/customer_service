"""workflow schedules cron timezone

Revision ID: s2a000000001
Revises: s1a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s2a000000001"
down_revision: Union[str, Sequence[str], None] = "s1a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_schedules",
        sa.Column("cron_expression", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_schedules", "cron_expression")
