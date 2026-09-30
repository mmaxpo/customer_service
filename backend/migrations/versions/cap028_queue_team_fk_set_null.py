"""set customer-service queue team FK to SET NULL

Revision ID: cap028
Revises: cap027
"""

from alembic import op


revision = "cap028"
down_revision = "cap027"
branch_labels = None
depends_on = None


_CONSTRAINT = "fk_cs_queues_team_id_cs_teams"


def upgrade() -> None:
    op.drop_constraint(
        _CONSTRAINT,
        "cs_queues",
        type_="foreignkey",
    )

    op.create_foreign_key(
        _CONSTRAINT,
        "cs_queues",
        "cs_teams",
        ["team_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        _CONSTRAINT,
        "cs_queues",
        type_="foreignkey",
    )

    op.create_foreign_key(
        _CONSTRAINT,
        "cs_queues",
        "cs_teams",
        ["team_id"],
        ["id"],
    )
