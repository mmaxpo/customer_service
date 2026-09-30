"""workflow wait claims

Revision ID: ww2a000000001
Revises: ww1a000000001
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ww2a000000001"
down_revision: Union[str, Sequence[str], None] = "ww1a000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_waits",
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "workflow_waits",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_workflow_waits_claimed_by", "workflow_waits", ["claimed_by"])
    op.create_index("ix_workflow_waits_claimed_at", "workflow_waits", ["claimed_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_waits_claimed_at", table_name="workflow_waits")
    op.drop_index("ix_workflow_waits_claimed_by", table_name="workflow_waits")
    op.drop_column("workflow_waits", "claimed_at")
    op.drop_column("workflow_waits", "claimed_by")
