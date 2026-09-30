"""rename agent runtime ids

Revision ID: 7baaa67cd8ef
Revises: 078f803aed08
Create Date: 2026-05-10 17:55:51.397036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7baaa67cd8ef'
down_revision: Union[str, Sequence[str], None] = '078f803aed08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.alter_column("agent_runs", "run_id", new_column_name="agent_run_id")

    op.alter_column("agent_run_events", "run_id", new_column_name="agent_run_id")

def downgrade() -> None:

    op.alter_column("agent_run_events", "agent_run_id", new_column_name="run_id")

    op.alter_column("agent_runs", "agent_run_id", new_column_name="run_id")
