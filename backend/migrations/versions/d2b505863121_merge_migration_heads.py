"""merge migration heads

Revision ID: d2b505863121
Revises: 7e28b3cd762a, 9e4258772a35, wd1a000000001
Create Date: 2026-05-29 12:37:23.890432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2b505863121'
down_revision: Union[str, Sequence[str], None] = ('7e28b3cd762a', '9e4258772a35', 'wd1a000000001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
