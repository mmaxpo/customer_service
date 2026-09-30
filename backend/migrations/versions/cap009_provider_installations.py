"""Add durable capability provider installations.

Revision ID: cap009
Revises: cap008
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap009"
down_revision = "cap008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capability_provider_installations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "scope_key",
            sa.String(length=1000),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "integration_kind",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "integration_connection_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "configuration_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "authentication_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "verification_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "failure_code",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "failure_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope_key",
            name="uq_cap_provider_installation_scope",
        ),
    )

    op.create_index(
        "ix_cap_provider_installations_user_id",
        "capability_provider_installations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_cap_provider_installations_tenant_id",
        "capability_provider_installations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_cap_provider_installations_provider_id",
        "capability_provider_installations",
        ["provider_id"],
        unique=False,
    )
    op.create_index(
        "ix_cap_provider_installations_integration_kind",
        "capability_provider_installations",
        ["integration_kind"],
        unique=False,
    )
    op.create_index(
        "ix_cap_provider_installations_integration_connection_id",
        "capability_provider_installations",
        ["integration_connection_id"],
        unique=False,
    )
    op.create_index(
        "ix_cap_provider_installation_owner_provider",
        "capability_provider_installations",
        ["user_id", "tenant_id", "provider_id"],
        unique=False,
    )
    op.create_index(
        "ix_cap_provider_installation_external_connection",
        "capability_provider_installations",
        [
            "integration_kind",
            "integration_connection_id",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cap_provider_installation_external_connection",
        table_name="capability_provider_installations",
    )
    op.drop_index(
        "ix_cap_provider_installation_owner_provider",
        table_name="capability_provider_installations",
    )
    op.drop_index(
        "ix_cap_provider_installations_integration_connection_id",
        table_name="capability_provider_installations",
    )
    op.drop_index(
        "ix_cap_provider_installations_integration_kind",
        table_name="capability_provider_installations",
    )
    op.drop_index(
        "ix_cap_provider_installations_provider_id",
        table_name="capability_provider_installations",
    )
    op.drop_index(
        "ix_cap_provider_installations_tenant_id",
        table_name="capability_provider_installations",
    )
    op.drop_index(
        "ix_cap_provider_installations_user_id",
        table_name="capability_provider_installations",
    )
    op.drop_table(
        "capability_provider_installations"
    )
