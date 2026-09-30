"""Add exact capability-health evaluation identity.

Revision ID: cap004
Revises: cap003
"""

from __future__ import annotations

import hashlib

from alembic import op
import sqlalchemy as sa


revision = "cap004"
down_revision = "cap003"
branch_labels = None
depends_on = None


TABLE = "capability_provider_health_decisions"
INDEX = (
    "ix_capability_provider_health_decisions_"
    "evaluation_key"
)


def _evaluation_key(
    *,
    user_id,
    tenant_id,
    capability_id,
    provider_id,
    provider_ref,
    window_start,
    window_end,
) -> str:
    """
    Match build_provider_health_evaluation_key() exactly.

    The runtime scope key is:
        user|tenant|capability|provider|provider_ref

    The evaluation key adds:
        window_start|window_end
    """

    scope_key = "|".join(
        (
            str(user_id),
            str(tenant_id or ""),
            str(capability_id or "").strip(),
            str(provider_id or "").strip(),
            str(provider_ref or ""),
        )
    )

    raw = "|".join(
        (
            scope_key,
            window_start.isoformat(),
            window_end.isoformat(),
        )
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "evaluation_key",
            sa.String(length=64),
            nullable=True,
        ),
    )

    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            f"""
            SELECT
                id,
                user_id,
                tenant_id,
                capability_id,
                provider_id,
                provider_ref,
                window_start,
                window_end
            FROM {TABLE}
            """
        )
    ).mappings().all()

    for row in rows:
        key = _evaluation_key(
            user_id=row["user_id"],
            tenant_id=row["tenant_id"],
            capability_id=row["capability_id"],
            provider_id=row["provider_id"],
            provider_ref=row["provider_ref"],
            window_start=row["window_start"],
            window_end=row["window_end"],
        )

        bind.execute(
            sa.text(
                f"""
                UPDATE {TABLE}
                SET evaluation_key = :evaluation_key
                WHERE id = :id
                """
            ),
            {
                "evaluation_key": key,
                "id": row["id"],
            },
        )

    # Historical retries may have persisted more than one decision for the
    # same exact scope/window. Keep the newest record because the projected
    # health-state row reflects the most recently applied decision.
    bind.execute(
        sa.text(
            f"""
            WITH ranked AS (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY evaluation_key
                        ORDER BY created_at DESC, id DESC
                    ) AS duplicate_rank
                FROM {TABLE}
            )
            DELETE FROM {TABLE} AS decision
            USING ranked
            WHERE decision.id = ranked.id
              AND ranked.duplicate_rank > 1
            """
        )
    )

    op.alter_column(
        TABLE,
        "evaluation_key",
        existing_type=sa.String(length=64),
        nullable=False,
    )

    op.create_index(
        INDEX,
        TABLE,
        ["evaluation_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        INDEX,
        table_name=TABLE,
    )
    op.drop_column(
        TABLE,
        "evaluation_key",
    )
