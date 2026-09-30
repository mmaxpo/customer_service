"""merge customer service phase1 heads

Revision ID: f1b000000001
Revises: 0d059ec6fe32, f1a000000001
Create Date: 2026-05-26
"""

from typing import Sequence, Union

revision: str = "f1b000000001"
down_revision: Union[str, Sequence[str], None] = (
    "0d059ec6fe32",
    "f1a000000001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
