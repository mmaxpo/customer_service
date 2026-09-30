"""Link SLA policies to merchant business calendars.

Revision ID: cap036
Revises: cap035
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap036"
down_revision = "cap035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cs_sla_policies",
        sa.Column("calendar_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cs_sla_policies_calendar",
        "cs_sla_policies",
        "cs_sla_calendars",
        ["calendar_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_cs_sla_policies_calendar_id", "cs_sla_policies", ["calendar_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_cs_sla_policies_calendar_id", table_name="cs_sla_policies")
    op.drop_constraint(
        "fk_cs_sla_policies_calendar", "cs_sla_policies", type_="foreignkey"
    )
    op.drop_column("cs_sla_policies", "calendar_id")
