"""Remember each user's light / dark theme choice.

Revision ID: ui01
Revises: cap056
"""

from alembic import op
import sqlalchemy as sa

revision = "ui01"
down_revision = "cap056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("ui_theme", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "ui_theme")
