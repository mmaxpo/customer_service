"""add customer identity registry

Revision ID: cap043
Revises: cap042
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap043"
down_revision = "cap042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_customer_identities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "identity_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "namespace",
            sa.String(length=320),
            nullable=False,
        ),
        sa.Column(
            "value",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column(
            "normalized_value",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "external_account_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "source",
            sa.String(length=64),
            nullable=True,
        ),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["cs_customers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "identity_type",
            "namespace",
            "normalized_value",
            name="uq_cs_customer_identity_scope",
        ),
    )

    op.create_index(
        "ix_cs_customer_identities_user_id",
        "cs_customer_identities",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_customer_identities_workspace_id",
        "cs_customer_identities",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_customer_identities_customer_id",
        "cs_customer_identities",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_customer_identities_identity_type",
        "cs_customer_identities",
        ["identity_type"],
        unique=False,
    )
    op.create_index(
        "ix_cs_customer_identities_customer",
        "cs_customer_identities",
        ["user_id", "customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_cs_customer_identities_lookup",
        "cs_customer_identities",
        [
            "user_id",
            "identity_type",
            "namespace",
            "normalized_value",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cs_customer_identities_lookup",
        table_name="cs_customer_identities",
    )
    op.drop_index(
        "ix_cs_customer_identities_customer",
        table_name="cs_customer_identities",
    )
    op.drop_index(
        "ix_cs_customer_identities_identity_type",
        table_name="cs_customer_identities",
    )
    op.drop_index(
        "ix_cs_customer_identities_customer_id",
        table_name="cs_customer_identities",
    )
    op.drop_index(
        "ix_cs_customer_identities_workspace_id",
        table_name="cs_customer_identities",
    )
    op.drop_index(
        "ix_cs_customer_identities_user_id",
        table_name="cs_customer_identities",
    )

    op.drop_table("cs_customer_identities")
