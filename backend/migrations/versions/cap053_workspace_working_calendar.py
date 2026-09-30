"""guarantee workspace IANA timezone and canonical working-calendar storage

Revision ID: cap053
Revises: cap052
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap053"
down_revision = "cap052"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("UPDATE workspaces SET timezone = 'UTC' WHERE timezone IS NULL")
    op.execute(
        "UPDATE workspaces SET business_hours = jsonb_build_object("
        "'mode', '24_7', 'weekly_hours', '{}'::jsonb, 'holidays', '[]'::jsonb, "
        "'out_of_hours', jsonb_build_object('widget_state', 'away', "
        "'auto_reply_enabled', false, 'auto_reply_text', null)) "
        "WHERE business_hours IS NULL"
    )
    op.alter_column("workspaces", "timezone", existing_type=sa.String(length=100), nullable=False, server_default="UTC")
    op.alter_column("workspaces", "business_hours", existing_type=postgresql.JSONB(), nullable=False)


def downgrade() -> None:
    op.alter_column("workspaces", "business_hours", existing_type=postgresql.JSONB(), nullable=True)
    op.alter_column("workspaces", "timezone", existing_type=sa.String(length=100), nullable=True, server_default=None)
