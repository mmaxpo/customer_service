"""customer service phase1 audit logs and macros

Revision ID: f1a000000001
Revises: e0966f68a0bd
Create Date: 2026-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f1a000000001"
down_revision: Union[str, Sequence[str], None] = "e0966f68a0bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_audit_logs_user_id", "cs_audit_logs", ["user_id"])
    op.create_index("ix_cs_audit_logs_entity_type", "cs_audit_logs", ["entity_type"])
    op.create_index("ix_cs_audit_logs_entity_id", "cs_audit_logs", ["entity_id"])
    op.create_index("ix_cs_audit_logs_action", "cs_audit_logs", ["action"])

    op.create_table(
        "cs_macros",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_macros_user_id", "cs_macros", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cs_macros_user_id", table_name="cs_macros")
    op.drop_table("cs_macros")
    op.drop_index("ix_cs_audit_logs_action", table_name="cs_audit_logs")
    op.drop_index("ix_cs_audit_logs_entity_id", table_name="cs_audit_logs")
    op.drop_index("ix_cs_audit_logs_entity_type", table_name="cs_audit_logs")
    op.drop_index("ix_cs_audit_logs_user_id", table_name="cs_audit_logs")
    op.drop_table("cs_audit_logs")
