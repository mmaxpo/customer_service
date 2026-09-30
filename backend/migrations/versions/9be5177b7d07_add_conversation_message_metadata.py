"""add conversation message metadata

Revision ID: 9be5177b7d07
Revises: f36c53747a72
Create Date: 2026-05-25 13:36:00.691805
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9be5177b7d07"
down_revision: Union[str, Sequence[str], None] = "f36c53747a72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cs_conversation_messages",
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("cs_conversation_messages", "meta")
