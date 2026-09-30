"""Secure Shopify installs, scopes, and webhook lifecycle.

Revision ID: cap032
Revises: cap031
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "cap032"
down_revision = "cap031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cs_shopify_connections",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "cs_shopify_connections",
        sa.Column("granted_scopes", sa.Text(), nullable=True),
    )
    op.add_column(
        "cs_shopify_connections",
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cs_shopify_connections",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cs_shopify_connections",
        sa.Column("reauth_required_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cs_shopify_connections_workspace_id_workspaces",
        "cs_shopify_connections",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_cs_shopify_connections_workspace_id",
        "cs_shopify_connections",
        ["workspace_id"],
    )
    op.execute(
        """
        UPDATE cs_shopify_connections AS connection
        SET workspace_id = workspace.id
        FROM workspaces AS workspace
        WHERE workspace.created_by_user_id = connection.user_id
          AND workspace.kind = 'personal'
          AND connection.workspace_id IS NULL
        """
    )

    op.create_table(
        "shopify_oauth_install_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "initiated_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by_user_id"], ["user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index(
        "ix_shopify_oauth_install_sessions_workspace_id",
        "shopify_oauth_install_sessions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_shopify_oauth_install_sessions_expires_at",
        "shopify_oauth_install_sessions",
        ["expires_at"],
    )

    op.create_table(
        "shopify_webhook_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("webhook_id", sa.String(length=255), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="processed",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("webhook_id"),
    )


def downgrade() -> None:
    op.drop_table("shopify_webhook_receipts")
    op.drop_table("shopify_oauth_install_sessions")
    op.drop_index(
        "ix_cs_shopify_connections_workspace_id",
        table_name="cs_shopify_connections",
    )
    op.drop_constraint(
        "fk_cs_shopify_connections_workspace_id_workspaces",
        "cs_shopify_connections",
        type_="foreignkey",
    )
    op.drop_column("cs_shopify_connections", "reauth_required_at")
    op.drop_column("cs_shopify_connections", "revoked_at")
    op.drop_column("cs_shopify_connections", "installed_at")
    op.drop_column("cs_shopify_connections", "granted_scopes")
    op.drop_column("cs_shopify_connections", "workspace_id")
