"""Persist provider-health probe completion.

Revision ID: cap007
Revises: cap006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap007"
down_revision = "cap006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "capability_performance_observations",
        sa.Column(
            "health_probe",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "capability_performance_observations",
        sa.Column(
            "health_probe_lease_token",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_capability_performance_observations_"
        "health_probe_lease_token",
        "capability_performance_observations",
        ["health_probe_lease_token"],
        unique=False,
    )

    op.create_table(
        "capability_provider_health_probe_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "state_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "lease_token",
            sa.String(length=64),
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
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "provider_ref",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "succeeded",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "previous_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "resulting_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "failure_kind",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "error_code",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "lease_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "cooldown_until",
            sa.DateTime(timezone=True),
            nullable=True,
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
        sa.ForeignKeyConstraint(
            ["state_id"],
            ["capability_provider_health_states.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lease_token"),
    )

    for name, columns in (
        (
            "ix_cap_provider_probe_results_state_id",
            ["state_id"],
        ),
        (
            "ix_cap_provider_probe_results_scope_key",
            ["scope_key"],
        ),
        (
            "ix_cap_provider_probe_results_user_id",
            ["user_id"],
        ),
        (
            "ix_cap_provider_probe_results_completed_at",
            ["completed_at"],
        ),
    ):
        op.create_index(
            name,
            "capability_provider_health_probe_results",
            columns,
            unique=False,
        )


def downgrade() -> None:
    for name in (
        "ix_cap_provider_probe_results_completed_at",
        "ix_cap_provider_probe_results_user_id",
        "ix_cap_provider_probe_results_scope_key",
        "ix_cap_provider_probe_results_state_id",
    ):
        op.drop_index(
            name,
            table_name=(
                "capability_provider_health_probe_results"
            ),
        )

    op.drop_table(
        "capability_provider_health_probe_results"
    )

    op.drop_index(
        "ix_capability_performance_observations_"
        "health_probe_lease_token",
        table_name=(
            "capability_performance_observations"
        ),
    )
    op.drop_column(
        "capability_performance_observations",
        "health_probe_lease_token",
    )
    op.drop_column(
        "capability_performance_observations",
        "health_probe",
    )
