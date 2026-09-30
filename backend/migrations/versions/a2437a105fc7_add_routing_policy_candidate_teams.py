"""add routing policy candidate teams

Revision ID: a2437a105fc7
Revises: d2b505863121
Create Date: 2026-05-29 12:45:55.489384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a2437a105fc7'
down_revision: Union[str, Sequence[str], None] = 'd2b505863121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(

        "cs_routing_policies",

        sa.Column(

            "candidate_team_ids",

            postgresql.JSONB(astext_type=sa.Text()),

            nullable=False,

            server_default=sa.text("'[]'::jsonb"),

        ),

    )

def downgrade() -> None:

    op.drop_column("cs_routing_policies", "candidate_team_ids")
