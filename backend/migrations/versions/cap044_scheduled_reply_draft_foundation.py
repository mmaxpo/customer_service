"""add scheduled reply draft foundation

Revision ID: cap044
Revises: cap043
Create Date: 2026-09-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "cap044"
down_revision = "cap043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cs_reply_drafts",
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "cs_reply_drafts",
        sa.Column(
            "scheduled_by_user_id",
            sa.UUID(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_cs_reply_drafts_scheduled_by_user",
        "cs_reply_drafts",
        "user",
        ["scheduled_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_cs_reply_drafts_scheduled_for",
        "cs_reply_drafts",
        ["scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_reply_drafts_scheduled_for",
        table_name="cs_reply_drafts",
    )

    op.drop_constraint(
        "fk_cs_reply_drafts_scheduled_by_user",
        "cs_reply_drafts",
        type_="foreignkey",
    )

    op.drop_column(
        "cs_reply_drafts",
        "scheduled_by_user_id",
    )

    op.drop_column(
        "cs_reply_drafts",
        "scheduled_for",
    )
