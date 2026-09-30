"""add workspace profile contact and locale settings

Revision ID: cap050
Revises: cap049
"""

from alembic import op
import sqlalchemy as sa


revision = "cap050"
down_revision = "cap049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("support_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("default_sender_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("default_sender_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "default_locale",
            sa.String(length=35),
            nullable=False,
            server_default=sa.text("'en'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "default_locale")
    op.drop_column("workspaces", "default_sender_email")
    op.drop_column("workspaces", "default_sender_name")
    op.drop_column("workspaces", "support_email")
