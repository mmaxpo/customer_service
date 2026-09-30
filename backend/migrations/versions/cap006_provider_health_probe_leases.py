"""Add durable provider-health probe leases.

Revision ID: cap006
Revises: cap005
"""

from alembic import op
import sqlalchemy as sa


revision = "cap006"
down_revision = "cap005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "capability_provider_health_states",
        sa.Column(
            "probe_lease_token",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "capability_provider_health_states",
        sa.Column(
            "probe_lease_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "capability_provider_health_states",
        sa.Column(
            "probe_claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_capability_provider_health_states_probe_lease_token",
        "capability_provider_health_states",
        ["probe_lease_token"],
        unique=False,
    )
    op.create_index(
        "ix_capability_provider_health_states_probe_lease_until",
        "capability_provider_health_states",
        ["probe_lease_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_capability_provider_health_states_probe_lease_until",
        table_name="capability_provider_health_states",
    )
    op.drop_index(
        "ix_capability_provider_health_states_probe_lease_token",
        table_name="capability_provider_health_states",
    )

    op.drop_column(
        "capability_provider_health_states",
        "probe_claimed_at",
    )
    op.drop_column(
        "capability_provider_health_states",
        "probe_lease_until",
    )
    op.drop_column(
        "capability_provider_health_states",
        "probe_lease_token",
    )
