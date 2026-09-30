"""merge sla business hours head

Revision ID: 66c4bf99457a
Revises: 20260616_add_sla_business_hours, 7c2f4d9a1e88
Create Date: 2026-06-16 14:07:44.735012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66c4bf99457a'
down_revision: Union[str, Sequence[str], None] = ('20260616_add_sla_business_hours', '7c2f4d9a1e88')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
