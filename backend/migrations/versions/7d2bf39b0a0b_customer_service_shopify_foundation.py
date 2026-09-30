"""customer service shopify foundation

Revision ID: 7d2bf39b0a0b
Revises: b76a968166e5
Create Date: 2026-05-27 09:27:14.244567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7d2bf39b0a0b'
down_revision: Union[str, Sequence[str], None] = 'b76a968166e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "cs_shopify_connections",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("shop_domain", sa.String(length=255), nullable=False),

        sa.Column("access_token_encrypted", sa.Text(), nullable=True),

        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

    )

    op.create_index("ix_cs_shopify_connections_user_id", "cs_shopify_connections", ["user_id"])

    op.create_index("ix_cs_shopify_connections_shop_domain", "cs_shopify_connections", ["shop_domain"])

    op.create_index("ix_cs_shopify_connections_status", "cs_shopify_connections", ["status"])

    op.create_table(

        "cs_shopify_order_cache",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("shop_domain", sa.String(length=255), nullable=False),

        sa.Column("order_id", sa.String(length=255), nullable=False),

        sa.Column("order_name", sa.String(length=255), nullable=True),

        sa.Column("customer_email", sa.String(length=255), nullable=True),

        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

    )

    op.create_index("ix_cs_shopify_order_cache_user_id", "cs_shopify_order_cache", ["user_id"])

    op.create_index("ix_cs_shopify_order_cache_shop_domain", "cs_shopify_order_cache", ["shop_domain"])

    op.create_index("ix_cs_shopify_order_cache_order_id", "cs_shopify_order_cache", ["order_id"])

    op.create_index("ix_cs_shopify_order_cache_order_name", "cs_shopify_order_cache", ["order_name"])

    op.create_index("ix_cs_shopify_order_cache_customer_email", "cs_shopify_order_cache", ["customer_email"])

def downgrade() -> None:

    op.drop_index("ix_cs_shopify_order_cache_customer_email", table_name="cs_shopify_order_cache")

    op.drop_index("ix_cs_shopify_order_cache_order_name", table_name="cs_shopify_order_cache")

    op.drop_index("ix_cs_shopify_order_cache_order_id", table_name="cs_shopify_order_cache")

    op.drop_index("ix_cs_shopify_order_cache_shop_domain", table_name="cs_shopify_order_cache")

    op.drop_index("ix_cs_shopify_order_cache_user_id", table_name="cs_shopify_order_cache")

    op.drop_table("cs_shopify_order_cache")

    op.drop_index("ix_cs_shopify_connections_status", table_name="cs_shopify_connections")

    op.drop_index("ix_cs_shopify_connections_shop_domain", table_name="cs_shopify_connections")

    op.drop_index("ix_cs_shopify_connections_user_id", table_name="cs_shopify_connections")

    op.drop_table("cs_shopify_connections")
