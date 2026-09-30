"""add objective repair lifecycle results

Revision ID: cap023
Revises: cap022
Create Date: 2026-08-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cap023"
down_revision: Union[str, None] = "cap022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "objective_repair_executions",
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "objective_repair_executions",
        sa.Column(
            "failure_code",
            sa.String(length=120),
            nullable=True,
        ),
    )
    op.add_column(
        "objective_repair_executions",
        sa.Column(
            "failure_message",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "objective_repair_executions",
        "failure_message",
    )
    op.drop_column(
        "objective_repair_executions",
        "failure_code",
    )
    op.drop_column(
        "objective_repair_executions",
        "result_json",
    )
