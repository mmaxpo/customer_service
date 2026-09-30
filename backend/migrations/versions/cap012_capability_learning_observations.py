"""add capability learning observations

Revision ID: cap012
Revises: cap011
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap012"
down_revision = "cap011"
branch_labels = None
depends_on = None


TABLE = "capability_learning_observations"


COLUMN_INDEXES = {
    "source_event_id": "ix_cap_learn_source_event",
    "source_verification_record_id": (
        "ix_cap_learn_verification_record"
    ),
    "verification_id": "ix_cap_learn_verification",
    "user_id": "ix_cap_learn_user",
    "tenant_id": "ix_cap_learn_tenant",
    "capability_id": "ix_cap_learn_capability",
    "provider_id": "ix_cap_learn_provider",
    "provider_ref": "ix_cap_learn_provider_ref",
    "action": "ix_cap_learn_action",
    "outcome": "ix_cap_learn_outcome",
    "method": "ix_cap_learn_method",
    "reason_code": "ix_cap_learn_reason",
    "retryable": "ix_cap_learn_retryable",
    "is_final": "ix_cap_learn_final",
    "correlation_id": "ix_cap_learn_correlation",
    "workflow_run_id": "ix_cap_learn_workflow",
    "task_id": "ix_cap_learn_task",
    "observed_at": "ix_cap_learn_observed",
    "created_at": "ix_cap_learn_created",
}


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_verification_record_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "verification_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "attempt_number",
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
            "outcome",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "method",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "reason_code",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "retryable",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "is_final",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "correlation_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "workflow_run_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "task_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "observed_outcome_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "evidence_summary_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "context_json",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "observation_json",
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
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["platform_events.id"],
            name="fk_cap_learn_event",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_verification_record_id"],
            ["task_verification_records.id"],
            name="fk_cap_learn_verify_record",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_event_id",
            name="uq_cap_learn_source_event",
        ),
        sa.UniqueConstraint(
            "source_verification_record_id",
            name="uq_cap_learn_verification_record",
        ),
        sa.UniqueConstraint(
            "user_id",
            "verification_id",
            "attempt_number",
            name=(
                "uq_cap_learning_user_"
                "verification_attempt"
            ),
        ),
    )

    for column, index_name in COLUMN_INDEXES.items():
        op.create_index(
            index_name,
            TABLE,
            [column],
            unique=False,
        )

    op.create_index(
        "ix_cap_learning_owner_observed",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "observed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_cap_learning_scope_outcome",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "action",
            "outcome",
            "observed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_cap_learning_final_scope",
        TABLE,
        [
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "is_final",
            "observed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_cap_learning_workflow_task",
        TABLE,
        [
            "user_id",
            "workflow_run_id",
            "task_id",
            "observed_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cap_learning_workflow_task",
        table_name=TABLE,
    )
    op.drop_index(
        "ix_cap_learning_final_scope",
        table_name=TABLE,
    )
    op.drop_index(
        "ix_cap_learning_scope_outcome",
        table_name=TABLE,
    )
    op.drop_index(
        "ix_cap_learning_owner_observed",
        table_name=TABLE,
    )

    for index_name in reversed(
        tuple(COLUMN_INDEXES.values())
    ):
        op.drop_index(
            index_name,
            table_name=TABLE,
        )

    op.drop_table(TABLE)
