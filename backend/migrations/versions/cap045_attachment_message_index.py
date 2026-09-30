"""index customer-service attachment message linkage

Revision ID: cap045
Revises: cap044
Create Date: 2026-09-12
"""

from __future__ import annotations

from alembic import op


revision = "cap045"
down_revision = "cap044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_cs_attachments_message_id",
        "cs_attachments",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_attachments_message_id",
        table_name="cs_attachments",
    )
