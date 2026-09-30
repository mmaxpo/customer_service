"""add workspace business profile fields

Revision ID: cap047
Revises: cap046
Create Date: 2026-09-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "cap047"
down_revision = "cap046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("business_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("timezone", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "business_hours",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "business_hours")
    op.drop_column("workspaces", "timezone")
    op.drop_column("workspaces", "business_name")
