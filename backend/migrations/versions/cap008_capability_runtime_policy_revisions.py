"""add durable capability runtime policy revisions

Revision ID: cap008
Revises: cap007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap008"
down_revision = "cap007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capability_runtime_policy_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "policy_key",
            sa.String(length=255),
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
            "capability_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_ref",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "policy_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_capability_runtime_policy_revisions",
        ),
        sa.UniqueConstraint(
            "scope_key",
            "version",
            name="uq_cap_runtime_policy_scope_version",
        ),
    )

    indexes = (
        (
            "ix_capability_runtime_policy_revisions_policy_key",
            ["policy_key"],
        ),
        (
            "ix_capability_runtime_policy_revisions_scope_key",
            ["scope_key"],
        ),
        (
            "ix_capability_runtime_policy_revisions_user_id",
            ["user_id"],
        ),
        (
            "ix_capability_runtime_policy_revisions_tenant_id",
            ["tenant_id"],
        ),
        (
            "ix_capability_runtime_policy_revisions_capability_id",
            ["capability_id"],
        ),
        (
            "ix_capability_runtime_policy_revisions_provider_id",
            ["provider_id"],
        ),
        (
            "ix_capability_runtime_policy_revisions_provider_ref",
            ["provider_ref"],
        ),
        (
            "ix_capability_runtime_policy_revisions_enabled",
            ["enabled"],
        ),
        (
            "ix_capability_runtime_policy_revisions_created_by_user_id",
            ["created_by_user_id"],
        ),
        (
            "ix_capability_runtime_policy_revisions_created_at",
            ["created_at"],
        ),
        (
            "ix_cap_runtime_policy_owner_scope_version",
            [
                "user_id",
                "tenant_id",
                "capability_id",
                "provider_id",
                "version",
            ],
        ),
        (
            "ix_cap_runtime_policy_provider_ref_version",
            ["provider_ref", "version"],
        ),
    )

    for name, columns in indexes:
        op.create_index(
            name,
            "capability_runtime_policy_revisions",
            columns,
        )


def downgrade() -> None:
    indexes = (
        "ix_cap_runtime_policy_provider_ref_version",
        "ix_cap_runtime_policy_owner_scope_version",
        "ix_capability_runtime_policy_revisions_created_at",
        "ix_capability_runtime_policy_revisions_created_by_user_id",
        "ix_capability_runtime_policy_revisions_enabled",
        "ix_capability_runtime_policy_revisions_provider_ref",
        "ix_capability_runtime_policy_revisions_provider_id",
        "ix_capability_runtime_policy_revisions_capability_id",
        "ix_capability_runtime_policy_revisions_tenant_id",
        "ix_capability_runtime_policy_revisions_user_id",
        "ix_capability_runtime_policy_revisions_scope_key",
        "ix_capability_runtime_policy_revisions_policy_key",
    )

    for name in indexes:
        op.drop_index(
            name,
            table_name="capability_runtime_policy_revisions",
        )

    op.drop_table(
        "capability_runtime_policy_revisions"
    )
