"""add user registration legal acceptance and canonical email

Revision ID: cap048
Revises: cap047
Create Date: 2026-09-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "cap048"
down_revision = "cap047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "normalized_email",
            sa.String(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE "user"
        SET normalized_email = lower(btrim(email))
        WHERE normalized_email IS NULL
        """
    )

    op.alter_column(
        "user",
        "normalized_email",
        existing_type=sa.String(),
        nullable=False,
    )

    op.create_index(
        "ix_user_normalized_email",
        "user",
        ["normalized_email"],
        unique=True,
    )

    op.add_column(
        "user",
        sa.Column(
            "terms_accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "terms_version",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "privacy_accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "privacy_version",
            sa.String(length=64),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "privacy_version")
    op.drop_column("user", "privacy_accepted_at")
    op.drop_column("user", "terms_version")
    op.drop_column("user", "terms_accepted_at")

    op.drop_index(
        "ix_user_normalized_email",
        table_name="user",
    )
    op.drop_column("user", "normalized_email")
