"""add capability learning insight candidate revisions

Revision ID: cap013
Revises: cap012
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap013"
down_revision = "cap012"
branch_labels = None
depends_on = None


TABLE = (
    "capability_learning_insight_candidate_revisions"
)


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
            "capability_id",
            sa.String(length=255),
            nullable=False,
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
            "action",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "kind",
            sa.String(length=100),
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
            "promotion_target",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "validation_passed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "promotion_eligible",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "evidence_fingerprint",
            sa.String(length=64),
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
            "promoted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "candidate_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id",
            "version",
            name=(
                "uq_cap_learning_candidate_id_version"
            ),
        ),
    )

    single_column_indexes = (
        ("ix_cap_learn_candidate_id", "candidate_id"),
        ("ix_cap_learn_candidate_user", "user_id"),
        ("ix_cap_learn_candidate_tenant", "tenant_id"),
        ("ix_cap_learn_candidate_capability", "capability_id"),
        ("ix_cap_learn_candidate_provider", "provider_id"),
        ("ix_cap_learn_candidate_provider_ref", "provider_ref"),
        ("ix_cap_learn_candidate_action", "action"),
        ("ix_cap_learn_candidate_kind", "kind"),
        ("ix_cap_learn_candidate_status", "status"),
        ("ix_cap_learn_candidate_approval", "approval_status"),
        ("ix_cap_learn_candidate_target", "promotion_target"),
        ("ix_cap_learn_candidate_validated", "validation_passed"),
        ("ix_cap_learn_candidate_eligible", "promotion_eligible"),
        ("ix_cap_learn_candidate_evidence", "evidence_fingerprint"),
        ("ix_cap_learn_candidate_reviewer", "reviewed_by_user_id"),
        ("ix_cap_learn_candidate_created", "created_at"),
    )

    for index_name, column in single_column_indexes:
        op.create_index(
            index_name,
            TABLE,
            [column],
            unique=False,
        )

    op.create_index(
        "ix_cap_learning_candidate_owner_created",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "created_at",
        ],
        unique=False,
    )
    op.create_index(
        "ix_cap_learning_candidate_owner_scope",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "action",
            "created_at",
        ],
        unique=False,
    )
    op.create_index(
        "ix_cap_learning_candidate_owner_status",
        TABLE,
        [
            "user_id",
            "status",
            "approval_status",
            "promotion_eligible",
            "created_at",
        ],
        unique=False,
    )
    op.create_index(
        "ix_cap_learning_candidate_fingerprint",
        TABLE,
        [
            "user_id",
            "evidence_fingerprint",
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cap_learning_candidate_fingerprint",
        table_name=TABLE,
    )
    op.drop_index(
        "ix_cap_learning_candidate_owner_status",
        table_name=TABLE,
    )
    op.drop_index(
        "ix_cap_learning_candidate_owner_scope",
        table_name=TABLE,
    )
    op.drop_index(
        "ix_cap_learning_candidate_owner_created",
        table_name=TABLE,
    )

    for index_name in reversed(
        (
            "ix_cap_learn_candidate_id",
            "ix_cap_learn_candidate_user",
            "ix_cap_learn_candidate_tenant",
            "ix_cap_learn_candidate_capability",
            "ix_cap_learn_candidate_provider",
            "ix_cap_learn_candidate_provider_ref",
            "ix_cap_learn_candidate_action",
            "ix_cap_learn_candidate_kind",
            "ix_cap_learn_candidate_status",
            "ix_cap_learn_candidate_approval",
            "ix_cap_learn_candidate_target",
            "ix_cap_learn_candidate_validated",
            "ix_cap_learn_candidate_eligible",
            "ix_cap_learn_candidate_evidence",
            "ix_cap_learn_candidate_reviewer",
            "ix_cap_learn_candidate_created",
        )
    ):
        op.drop_index(
            index_name,
            table_name=TABLE,
        )

    op.drop_table(TABLE)
