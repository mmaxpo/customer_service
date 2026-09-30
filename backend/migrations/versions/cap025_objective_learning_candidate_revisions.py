"""add objective learning candidate revisions

Revision ID: cap025
Revises: cap024
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap025"
down_revision = "cap024"
branch_labels = None
depends_on = None


TABLE = "objective_learning_candidate_revisions"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
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
            "objective_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "schema_ref",
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
            "extractor_ref",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "extractor_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "approval_status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "validation_passed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "scope_fingerprint",
            sa.String(length=64),
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
            "reviewed_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "proposed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "validated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "candidate_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
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
            name=("pk_objective_learning_candidate_revisions"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "candidate_id",
            "version",
            name=("uq_objective_learning_candidate_revision"),
        ),
    )

    single_indexes = (
        "candidate_id",
        "user_id",
        "tenant_id",
        "objective_namespace",
        "objective_type",
        "schema_ref",
        "profile_ref",
        "extractor_ref",
        "status",
        "approval_status",
        "validation_passed",
        "scope_fingerprint",
        "policy_ref",
        "reviewed_by_user_id",
        "created_at",
    )

    for column in single_indexes:
        op.create_index(
            (f"ix_objective_learning_candidate_{column}"),
            TABLE,
            [column],
            unique=False,
        )

    op.create_index(
        "ix_objective_learning_candidate_owner_scope",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_objective_learning_candidate_owner_status",
        TABLE,
        [
            "user_id",
            "status",
            "approval_status",
            "created_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_objective_learning_candidate_fingerprint",
        TABLE,
        [
            "user_id",
            "scope_fingerprint",
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    for name in (
        "ix_objective_learning_candidate_fingerprint",
        "ix_objective_learning_candidate_owner_status",
        "ix_objective_learning_candidate_owner_scope",
    ):
        op.drop_index(
            name,
            table_name=TABLE,
        )

    for column in reversed(
        (
            "candidate_id",
            "user_id",
            "tenant_id",
            "objective_namespace",
            "objective_type",
            "schema_ref",
            "profile_ref",
            "extractor_ref",
            "status",
            "approval_status",
            "validation_passed",
            "scope_fingerprint",
            "policy_ref",
            "reviewed_by_user_id",
            "created_at",
        )
    ):
        op.drop_index(
            (f"ix_objective_learning_candidate_{column}"),
            table_name=TABLE,
        )

    op.drop_table(TABLE)
