"""add routing policy candidate queues

Revision ID: a3e14571c969
Revises: 435a6f069a11
Create Date: 2026-05-29 13:25:14.985659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3e14571c969'
down_revision: Union[str, Sequence[str], None] = '435a6f069a11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(

        "cs_routing_policies",

        sa.Column(

            "candidate_queue_ids",

            postgresql.JSONB(astext_type=sa.Text()),

            nullable=False,

            server_default=sa.text("'[]'::jsonb"),

        ),

    )

def downgrade() -> None:

    op.drop_column("cs_routing_policies", "candidate_queue_ids")
