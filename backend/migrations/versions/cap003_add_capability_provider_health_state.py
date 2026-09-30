"""add scoped capability provider health state

Revision ID: cap003
Revises: cap002
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cap003"
down_revision: Union[str, Sequence[str], None] = "cap002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capability_provider_health_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "scope_key",
            sa.String(length=1000),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
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
            "current_state",
            sa.String(length=50),
            nullable=False,
            server_default="healthy",
        ),
        sa.Column(
            "qualifying_recommendation",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "qualifying_windows",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "cooldown_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "manual_override_state",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "manual_override_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "manual_override_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "last_evaluated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope_key",
            name="uq_capability_provider_health_states_scope_key",
        ),
    )

    for column in (
        "scope_key",
        "user_id",
        "tenant_id",
        "capability_id",
        "provider_id",
        "provider_ref",
        "current_state",
        "cooldown_until",
        "manual_override_until",
    ):
        op.create_index(
            f"ix_capability_provider_health_states_{column}",
            "capability_provider_health_states",
            [column],
            unique=False,
        )

    op.create_index(
        "ix_cap_health_state_user_scope",
        "capability_provider_health_states",
        [
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
        ],
        unique=False,
    )
    op.create_index(
        "ix_cap_health_state_provider_status",
        "capability_provider_health_states",
        [
            "provider_id",
            "current_state",
            "updated_at",
        ],
        unique=False,
    )

    op.create_table(
        "capability_provider_health_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("state_id", sa.UUID(), nullable=False),
        sa.Column(
            "decision_key",
            sa.String(length=1000),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
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
            "previous_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "proposed_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "resulting_state",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "action",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "evidence_recommendation",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "evidence_sufficient",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "qualifying_windows",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "required_windows",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "window_start",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "window_end",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "cooldown_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "explanation",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "state_version",
            sa.Integer(),
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
        sa.UniqueConstraint(
            "decision_key",
            name=(
                "uq_capability_provider_health_decisions_"
                "decision_key"
            ),
        ),
    )

    for column in (
        "state_id",
        "decision_key",
        "user_id",
        "tenant_id",
        "capability_id",
        "provider_id",
        "action",
        "reason",
        "window_end",
        "evaluated_at",
    ):
        op.create_index(
            f"ix_capability_provider_health_decisions_{column}",
            "capability_provider_health_decisions",
            [column],
            unique=False,
        )

    op.create_index(
        "ix_cap_health_decision_scope_time",
        "capability_provider_health_decisions",
        [
            "user_id",
            "tenant_id",
            "capability_id",
            "provider_id",
            "evaluated_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table(
        "capability_provider_health_decisions"
    )
    op.drop_table(
        "capability_provider_health_states"
    )
