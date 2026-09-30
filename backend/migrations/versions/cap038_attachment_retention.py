"""Add attachment retention lifecycle.

Revision ID: cap038
Revises: cap037
"""

from alembic import op
import sqlalchemy as sa


revision = "cap038"
down_revision = "cap037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cs_attachments",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cs_attachments",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cs_attachments_expires_at", "cs_attachments", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_cs_attachments_expires_at", table_name="cs_attachments")
    op.drop_column("cs_attachments", "deleted_at")
    op.drop_column("cs_attachments", "expires_at")
