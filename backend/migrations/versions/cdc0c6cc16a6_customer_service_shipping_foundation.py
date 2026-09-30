"""customer service shipping foundation

Revision ID: cdc0c6cc16a6
Revises: 7d2bf39b0a0b
Create Date: 2026-05-27 09:32:25.465690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cdc0c6cc16a6'
down_revision: Union[str, Sequence[str], None] = '7d2bf39b0a0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "cs_shipping_tracking_cache",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("provider", sa.String(length=100), nullable=False),

        sa.Column("tracking_number", sa.String(length=255), nullable=False),

        sa.Column("status", sa.String(length=100), nullable=True),

        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

    )

    op.create_index("ix_cs_shipping_tracking_cache_user_id", "cs_shipping_tracking_cache", ["user_id"])

    op.create_index("ix_cs_shipping_tracking_cache_provider", "cs_shipping_tracking_cache", ["provider"])

    op.create_index("ix_cs_shipping_tracking_cache_tracking_number", "cs_shipping_tracking_cache", ["tracking_number"])

    op.create_index("ix_cs_shipping_tracking_cache_status", "cs_shipping_tracking_cache", ["status"])

def downgrade() -> None:

    op.drop_index("ix_cs_shipping_tracking_cache_status", table_name="cs_shipping_tracking_cache")

    op.drop_index("ix_cs_shipping_tracking_cache_tracking_number", table_name="cs_shipping_tracking_cache")

    op.drop_index("ix_cs_shipping_tracking_cache_provider", table_name="cs_shipping_tracking_cache")

    op.drop_index("ix_cs_shipping_tracking_cache_user_id", table_name="cs_shipping_tracking_cache")

    op.drop_table("cs_shipping_tracking_cache")
