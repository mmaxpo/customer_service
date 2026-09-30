"""add customer support outcomes

Revision ID: cap017
Revises: cap016
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cap017"
down_revision = "cap016"
branch_labels = None
depends_on = None

TABLE = "cs_support_outcomes"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_plan_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("objective_namespace", sa.String(length=100), nullable=False),
        sa.Column("objective_ref", sa.String(length=128), nullable=False),
        sa.Column("source_objective_version", sa.Integer(), nullable=False),
        sa.Column("outcome_version", sa.Integer(), nullable=False),
        sa.Column("objective_type", sa.String(length=100), nullable=False),
        sa.Column("order_ref", sa.String(length=255), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("operation_count", sa.Integer(), nullable=False),
        sa.Column("customer_message", sa.Text(), nullable=False),
        sa.Column("operations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outcome_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recording_idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "review_plan_id", name="uq_cs_support_outcomes_user_review_plan"),
    )
    for name, cols in [
        ("ix_cs_support_outcomes_user_id", ["user_id"]),
        ("ix_cs_support_outcomes_workflow_run_id", ["workflow_run_id"]),
        ("ix_cs_support_outcomes_chat_session_id", ["chat_session_id"]),
        ("ix_cs_support_outcomes_conversation_id", ["conversation_id"]),
        ("ix_cs_support_outcomes_objective_ref", ["objective_ref"]),
        ("ix_cs_support_outcomes_objective_type", ["objective_type"]),
        ("ix_cs_support_outcomes_order_ref", ["order_ref"]),
        ("ix_cs_support_outcomes_decision", ["decision"]),
        ("ix_cs_support_outcomes_status", ["status"]),
        ("ix_cs_support_outcomes_recording_idempotency_key", ["recording_idempotency_key"]),
        ("ix_cs_support_outcomes_user_created", ["user_id", "created_at"]),
        ("ix_cs_support_outcomes_user_conversation_created", ["user_id", "conversation_id", "created_at"]),
    ]:
        op.create_index(name, TABLE, cols, unique=False)


def downgrade() -> None:
    op.drop_table(TABLE)
