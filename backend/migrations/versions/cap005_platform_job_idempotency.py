"""Add durable platform-job idempotency.

Revision ID: cap005
Revises: cap004
"""

from alembic import op
import sqlalchemy as sa


revision = "cap005"
down_revision = "cap004"
branch_labels = None
depends_on = None


INDEX_NAME = "uq_platform_jobs_type_idempotency_key"


def upgrade() -> None:
    op.add_column(
        "platform_jobs",
        sa.Column(
            "idempotency_key",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        INDEX_NAME,
        "platform_jobs",
        ["job_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "idempotency_key IS NOT NULL"
        ),
    )

    op.create_index(
        "ix_cap_perf_health_scope_observed",
        "capability_performance_observations",
        [
            "observed_at",
            "tenant_id",
            "resolved_capability_id",
            "provider_id",
            "provider_ref",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cap_perf_health_scope_observed",
        table_name=(
            "capability_performance_observations"
        ),
    )
    op.drop_index(
        INDEX_NAME,
        table_name="platform_jobs",
    )
    op.drop_column(
        "platform_jobs",
        "idempotency_key",
    )
