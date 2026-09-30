"""add ticket assignments

Revision ID: e0966f68a0bd
Revises: d13c4e9e4fbb
Create Date: 2026-05-26 17:47:15.707703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e0966f68a0bd'
down_revision: Union[str, Sequence[str], None] = 'd13c4e9e4fbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "cs_ticket_assignments",

        sa.Column("id", sa.UUID(), nullable=False),

        sa.Column("user_id", sa.UUID(), nullable=False),

        sa.Column("ticket_id", sa.UUID(), nullable=False),

        sa.Column("assigned_to", sa.UUID(), nullable=True),

        sa.Column("assigned_by", sa.UUID(), nullable=True),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),

        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),

        sa.ForeignKeyConstraint(["ticket_id"], ["cs_tickets.id"]),

        sa.PrimaryKeyConstraint("id"),

    )

    op.create_index(

        "ix_cs_ticket_assignments_user_id",

        "cs_ticket_assignments",

        ["user_id"],

    )

    op.create_index(

        "ix_cs_ticket_assignments_ticket_id",

        "cs_ticket_assignments",

        ["ticket_id"],

    )

    op.create_index(

        "ix_cs_ticket_assignments_assigned_to",

        "cs_ticket_assignments",

        ["assigned_to"],

    )

def downgrade() -> None:

    op.drop_index("ix_cs_ticket_assignments_assigned_to", table_name="cs_ticket_assignments")

    op.drop_index("ix_cs_ticket_assignments_ticket_id", table_name="cs_ticket_assignments")

    op.drop_index("ix_cs_ticket_assignments_user_id", table_name="cs_ticket_assignments")

    op.drop_table("cs_ticket_assignments")
