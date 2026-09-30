"""add objective learning policy revisions

Revision ID: cap026
Revises: cap025
Create Date: 2026-08-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap026"
down_revision = "cap025"
branch_labels = None
depends_on = None


TABLE = "objective_learning_policy_revisions"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "scope_key",
            sa.String(length=1500),
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
            "objective_namespace",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "objective_type",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "profile_ref",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "profile_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "policy_ref",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "policy_version",
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
            "profile_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
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
            "informational_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "authorizes_execution",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_objective_learning_policy_revisions",
        ),
        sa.UniqueConstraint(
            "user_id",
            "scope_key",
            "policy_version",
            name="uq_objective_learning_policy_scope_version",
        ),
    )

    single_indexes = (
        "scope_key",
        "user_id",
        "tenant_id",
        "objective_namespace",
        "objective_type",
        "profile_ref",
        "policy_ref",
        "enabled",
        "created_by_user_id",
        "created_at",
    )

    for column in single_indexes:
        op.create_index(
            f"ix_objective_learning_policy_{column}",
            TABLE,
            [column],
            unique=False,
        )

    op.create_index(
        "ix_objective_learning_policy_owner_scope_version",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "profile_ref",
            "policy_ref",
            "policy_version",
        ],
        unique=False,
    )

    op.create_index(
        "ix_objective_learning_policy_owner_created",
        TABLE,
        [
            "user_id",
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    for name in (
        "ix_objective_learning_policy_owner_created",
        "ix_objective_learning_policy_owner_scope_version",
    ):
        op.drop_index(
            name,
            table_name=TABLE,
        )

    for column in reversed(
        (
            "scope_key",
            "user_id",
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "profile_ref",
            "policy_ref",
            "enabled",
            "created_by_user_id",
            "created_at",
        )
    ):
        op.drop_index(
            f"ix_objective_learning_policy_{column}",
            table_name=TABLE,
        )

    op.drop_table(TABLE)
