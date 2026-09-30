"""add sla business hours

Revision ID: 20260616_add_sla_business_hours
Revises: 
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260616_add_sla_business_hours"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cs_sla_policies",
        sa.Column("business_hours", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("cs_sla_policies", "business_hours")
