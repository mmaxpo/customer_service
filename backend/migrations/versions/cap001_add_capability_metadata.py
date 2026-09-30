"""add capability metadata

Revision ID: cap001
Revises: csi000000001
Create Date: 2026-07-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cap001"
down_revision: Union[str, Sequence[str], None] = "csi000000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capability_metadata",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("capability_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_capability_metadata_capability_id",
        "capability_metadata",
        ["capability_id"],
        unique=False,
    )
    op.create_index(
        "ix_capability_metadata_tenant_id",
        "capability_metadata",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_capability_metadata_domain",
        "capability_metadata",
        ["domain"],
        unique=False,
    )
    op.create_index(
        "ix_capability_metadata_category",
        "capability_metadata",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_capability_metadata_status",
        "capability_metadata",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_capability_metadata_capability_tenant",
        "capability_metadata",
        ["capability_id", "tenant_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_capability_metadata_capability_tenant", table_name="capability_metadata")
    op.drop_index("ix_capability_metadata_status", table_name="capability_metadata")
    op.drop_index("ix_capability_metadata_category", table_name="capability_metadata")
    op.drop_index("ix_capability_metadata_domain", table_name="capability_metadata")
    op.drop_index("ix_capability_metadata_tenant_id", table_name="capability_metadata")
    op.drop_index("ix_capability_metadata_capability_id", table_name="capability_metadata")
    op.drop_table("capability_metadata")
