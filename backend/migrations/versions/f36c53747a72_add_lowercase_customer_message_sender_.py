"""add lowercase customer message sender type

Revision ID: f36c53747a72
Revises: b027b73e2afc
Create Date: 2026-05-25 12:28:08.871884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f36c53747a72'
down_revision: Union[str, Sequence[str], None] = 'b027b73e2afc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE messagesendertype ADD VALUE IF NOT EXISTS 'customer'")
    op.execute("""
        UPDATE cs_conversation_messages
        SET sender_type = lower(sender_type::text)::messagesendertype
        WHERE sender_type::text IN ('CUSTOMER', 'AGENT', 'AI', 'SYSTEM', 'INTERNAL_NOTE')
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
