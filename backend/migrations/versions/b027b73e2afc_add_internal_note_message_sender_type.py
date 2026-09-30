"""add internal note message sender type

Revision ID: b027b73e2afc
Revises: 9dec80c98d7c
Create Date: 2026-05-25 10:28:00.750017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b027b73e2afc'
down_revision: Union[str, Sequence[str], None] = '9dec80c98d7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.execute("ALTER TYPE messagesendertype ADD VALUE IF NOT EXISTS 'agent'")

    op.execute("ALTER TYPE messagesendertype ADD VALUE IF NOT EXISTS 'ai'")

    op.execute("ALTER TYPE messagesendertype ADD VALUE IF NOT EXISTS 'system'")

    op.execute("ALTER TYPE messagesendertype ADD VALUE IF NOT EXISTS 'internal_note'")

def downgrade() -> None:

    pass
