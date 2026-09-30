"""add customer service sla"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d13c4e9e4fbb"
down_revision: Union[str, Sequence[str], None] = "b046ed1ffd7c"
branch_labels = None
depends_on = None


# Existing enum (already created by Ticket model)
ticket_priority = postgresql.ENUM(
    "LOW",
    "NORMAL",
    "HIGH",
    "URGENT",
    name="ticketpriority",
    create_type=False,
)

sla_target_type = postgresql.ENUM(
    "first_response",
    "resolution",
    name="slatargettype",
    create_type=False,
)

sla_violation_status = postgresql.ENUM(
    "open",
    "resolved",
    name="slaviolationstatus",
    create_type=False,
)


def upgrade():

    bind = op.get_bind()

    # create ONLY new enums
    sla_target_type.create(bind, checkfirst=True)
    sla_violation_status.create(bind, checkfirst=True)

    op.create_table(
        "cs_sla_policies",

        sa.Column("id", sa.UUID(), nullable=False),

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "priority",
            ticket_priority,
            nullable=False,
        ),

        sa.Column(
            "first_response_minutes",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "resolution_minutes",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
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
    )

    op.create_index(
        "ix_cs_sla_policies_user_id",
        "cs_sla_policies",
        ["user_id"],
    )

    op.create_table(
        "cs_sla_violations",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "ticket_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "policy_id",
            sa.UUID(),
            nullable=True,
        ),

        sa.Column(
            "target_type",
            sla_target_type,
            nullable=False,
        ),

        sa.Column(
            "due_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "breached_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "status",
            sla_violation_status,
            nullable=False,
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

        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["cs_tickets.id"],
        ),

        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["cs_sla_policies.id"],
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_cs_sla_violations_user_id",
        "cs_sla_violations",
        ["user_id"],
    )

    op.create_index(
        "ix_cs_sla_violations_ticket_id",
        "cs_sla_violations",
        ["ticket_id"],
    )

    op.create_index(
        "ix_cs_sla_violations_due_at",
        "cs_sla_violations",
        ["due_at"],
    )


def downgrade():

    op.drop_table("cs_sla_violations")
    op.drop_table("cs_sla_policies")

    bind = op.get_bind()

    sla_violation_status.drop(bind, checkfirst=True)
    sla_target_type.drop(bind, checkfirst=True)