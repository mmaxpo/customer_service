"""support multiple Shopify stores per workspace

Revision ID: cap052
Revises: cap051
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap052"
down_revision = "cap051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cs_shopify_connections",
        sa.Column(
            "business_hours_override",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "cs_shopify_connections",
        sa.Column("timezone_override", sa.String(length=100), nullable=True),
    )
    # Older development databases allowed repeated installs for the same
    # workspace/store. Keep the newest workspace-owned row before adding the
    # durable uniqueness guarantee. Rows with NULL workspace_id are legacy
    # records and remain valid because PostgreSQL permits multiple NULLs in a
    # unique constraint.
    op.execute(
        sa.text(
            """
            DELETE FROM cs_shopify_connections AS duplicate
            USING cs_shopify_connections AS keeper
            WHERE duplicate.workspace_id IS NOT NULL
              AND duplicate.workspace_id = keeper.workspace_id
              AND duplicate.shop_domain = keeper.shop_domain
              AND (
                  duplicate.updated_at < keeper.updated_at
                  OR (
                      duplicate.updated_at = keeper.updated_at
                      AND duplicate.created_at < keeper.created_at
                  )
                  OR (
                      duplicate.updated_at = keeper.updated_at
                      AND duplicate.created_at = keeper.created_at
                      AND duplicate.id < keeper.id
                  )
              )
            """
        )
    )
    # OAuth writes normalized domains.  This guards the durable workspace/store
    # identity and makes reconnects an update instead of a second active store.
    op.create_unique_constraint(
        "uq_cs_shopify_connection_workspace_shop",
        "cs_shopify_connections",
        ["workspace_id", "shop_domain"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_cs_shopify_connection_workspace_shop",
        "cs_shopify_connections",
        type_="unique",
    )
    op.drop_column("cs_shopify_connections", "timezone_override")
    op.drop_column("cs_shopify_connections", "business_hours_override")
