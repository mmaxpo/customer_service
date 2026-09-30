"""add capability learning insight promotion records

Revision ID: cap014
Revises: cap013
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap014"
down_revision = "cap013"
branch_labels = None
depends_on = None


TABLE = (
    "capability_learning_insight_promotion_records"
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
            "promotion_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "event_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "candidate_version",
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
            "event_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "promotion_target",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "evidence_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "promotion_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
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
            "promotion_id",
            "event_version",
            name=(
                "uq_cap_learning_promotion_event_version"
            ),
        ),
    )

    indexes = (
        (
            "ix_cap_learn_promotion_id",
            ["promotion_id"],
        ),
        (
            "ix_cap_learn_promotion_candidate",
            ["candidate_id"],
        ),
        (
            "ix_cap_learn_promotion_user",
            ["user_id"],
        ),
        (
            "ix_cap_learn_promotion_tenant",
            ["tenant_id"],
        ),
        (
            "ix_cap_learn_promotion_capability",
            ["capability_id"],
        ),
        (
            "ix_cap_learn_promotion_provider",
            ["provider_id"],
        ),
        (
            "ix_cap_learn_promotion_provider_ref",
            ["provider_ref"],
        ),
        (
            "ix_cap_learn_promotion_action",
            ["action"],
        ),
        (
            "ix_cap_learn_promotion_event",
            ["event_type"],
        ),
        (
            "ix_cap_learn_promotion_status",
            ["status"],
        ),
        (
            "ix_cap_learn_promotion_target",
            ["promotion_target"],
        ),
        (
            "ix_cap_learn_promotion_evidence",
            ["evidence_fingerprint"],
        ),
        (
            "ix_cap_learn_promotion_creator",
            ["created_by_user_id"],
        ),
        (
            "ix_cap_learn_promotion_created",
            ["created_at"],
        ),
        (
            "ix_cap_learning_promotion_owner_created",
            [
                "user_id",
                "tenant_id",
                "created_at",
            ],
        ),
        (
            "ix_cap_learning_promotion_candidate",
            [
                "user_id",
                "candidate_id",
                "created_at",
            ],
        ),
        (
            "ix_cap_learning_promotion_owner_status",
            [
                "user_id",
                "status",
                "promotion_target",
                "created_at",
            ],
        ),
        (
            "ix_cap_learning_promotion_scope",
            [
                "user_id",
                "tenant_id",
                "capability_id",
                "provider_id",
                "action",
                "created_at",
            ],
        ),
    )

    for index_name, columns in indexes:
        op.create_index(
            index_name,
            TABLE,
            columns,
            unique=False,
        )


def downgrade() -> None:
    indexes = (
        "ix_cap_learn_promotion_id",
        "ix_cap_learn_promotion_candidate",
        "ix_cap_learn_promotion_user",
        "ix_cap_learn_promotion_tenant",
        "ix_cap_learn_promotion_capability",
        "ix_cap_learn_promotion_provider",
        "ix_cap_learn_promotion_provider_ref",
        "ix_cap_learn_promotion_action",
        "ix_cap_learn_promotion_event",
        "ix_cap_learn_promotion_status",
        "ix_cap_learn_promotion_target",
        "ix_cap_learn_promotion_evidence",
        "ix_cap_learn_promotion_creator",
        "ix_cap_learn_promotion_created",
        "ix_cap_learning_promotion_owner_created",
        "ix_cap_learning_promotion_candidate",
        "ix_cap_learning_promotion_owner_status",
        "ix_cap_learning_promotion_scope",
    )

    for index_name in reversed(indexes):
        op.drop_index(
            index_name,
            table_name=TABLE,
        )

    op.drop_table(TABLE)
