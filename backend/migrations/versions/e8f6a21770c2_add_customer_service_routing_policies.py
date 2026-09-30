"""add customer service routing policies

Revision ID: e8f6a21770c2
Revises: 9a0ec515acfe
Create Date: 2026-05-28 20:46:07.345777

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e8f6a21770c2'
down_revision: Union[str, Sequence[str], None] = '9a0ec515acfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "cs_routing_policies",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),

        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("name", sa.String(length=255), nullable=False),

        sa.Column("channel", sa.String(length=64), nullable=True),

        sa.Column("intent", sa.String(length=100), nullable=True),

        sa.Column("priority", sa.String(length=50), nullable=True),

        sa.Column("strategy", sa.String(length=50), nullable=False, server_default="least_loaded"),

        sa.Column("candidate_assignee_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),

        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.UniqueConstraint("user_id", "name", name="uq_cs_routing_policy_name"),

    )

    op.create_index("ix_cs_routing_policies_user_id", "cs_routing_policies", ["user_id"])

    op.create_index("ix_cs_routing_policies_channel", "cs_routing_policies", ["channel"])

    op.create_index("ix_cs_routing_policies_intent", "cs_routing_policies", ["intent"])

    op.create_index("ix_cs_routing_policies_priority", "cs_routing_policies", ["priority"])

def downgrade() -> None:

    op.drop_index("ix_cs_routing_policies_priority", table_name="cs_routing_policies")

    op.drop_index("ix_cs_routing_policies_intent", table_name="cs_routing_policies")

    op.drop_index("ix_cs_routing_policies_channel", table_name="cs_routing_policies")

    op.drop_index("ix_cs_routing_policies_user_id", table_name="cs_routing_policies")

    op.drop_table("cs_routing_policies")
