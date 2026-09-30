"""add routing policy priority fallback

Revision ID: 7e28b3cd762a
Revises: e8f6a21770c2
Create Date: 2026-05-28 21:56:54.870235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e28b3cd762a'
down_revision: Union[str, Sequence[str], None] = 'e8f6a21770c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(

        "cs_routing_policies",

        sa.Column("priority_rank", sa.Integer(), nullable=False, server_default="100"),

    )

    op.add_column(

        "cs_routing_policies",

        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.false()),

    )

    op.create_index("ix_cs_routing_policies_priority_rank", "cs_routing_policies", ["priority_rank"])

    op.create_index("ix_cs_routing_policies_is_fallback", "cs_routing_policies", ["is_fallback"])

def downgrade() -> None:

    op.drop_index("ix_cs_routing_policies_is_fallback", table_name="cs_routing_policies")

    op.drop_index("ix_cs_routing_policies_priority_rank", table_name="cs_routing_policies")

    op.drop_column("cs_routing_policies", "is_fallback")

    op.drop_column("cs_routing_policies", "priority_rank")
