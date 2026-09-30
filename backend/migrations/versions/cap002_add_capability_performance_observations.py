"""add capability performance observations

Revision ID: cap002
Revises: cap001
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cap002"
down_revision: Union[str, Sequence[str], None] = "cap001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capability_performance_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_event_id", sa.UUID(), nullable=False),
        sa.Column(
            "correlation_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column(
            "requested_capability_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "resolved_capability_id",
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
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column(
            "error_code",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "failure_kind",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "exception_type",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "fallback_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "fallback_used",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "final_attempt",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "user_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "tenant_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "workflow_run_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "planner_session_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "thread_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "observation_json",
            postgresql.JSONB(astext_type=sa.Text()),
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
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_event_id",
            "attempt_index",
            name=(
                "uq_capability_performance_observation_"
                "event_attempt"
            ),
        ),
    )

    simple_indexes = [
        "source_event_id",
        "correlation_id",
        "requested_capability_id",
        "resolved_capability_id",
        "provider_id",
        "provider_ref",
        "status",
        "error_code",
        "failure_kind",
        "user_id",
        "tenant_id",
        "workflow_run_id",
        "planner_session_id",
        "thread_id",
        "created_at",
    ]

    for column in simple_indexes:
        op.create_index(
            f"ix_capability_performance_observations_{column}",
            "capability_performance_observations",
            [column],
            unique=False,
        )

    op.create_index(
        "ix_cap_perf_capability_provider_created",
        "capability_performance_observations",
        [
            "resolved_capability_id",
            "provider_id",
            "created_at",
        ],
        unique=False,
    )
    op.create_index(
        "ix_cap_perf_tenant_capability_provider_created",
        "capability_performance_observations",
        [
            "tenant_id",
            "resolved_capability_id",
            "provider_id",
            "created_at",
        ],
        unique=False,
    )
    op.create_index(
        "ix_cap_perf_provider_failure_created",
        "capability_performance_observations",
        [
            "provider_id",
            "failure_kind",
            "created_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("capability_performance_observations")
