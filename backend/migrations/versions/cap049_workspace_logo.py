"""add optional workspace logo URL

Revision ID: cap049
Revises: cap048
"""

from alembic import op
import sqlalchemy as sa


revision = "cap049"
down_revision = "cap048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "logo_url")
