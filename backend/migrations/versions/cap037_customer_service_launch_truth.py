"""Customer-service launch provider and knowledge truth.

Revision ID: cap037
Revises: cap036
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cap037"
down_revision = "cap036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cs_email_identities",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_name", sa.String(length=120), nullable=False),
        sa.Column("from_email", sa.String(length=320), nullable=False),
        sa.Column("reply_to", sa.String(length=320), nullable=True),
        sa.Column("provider_domain_id", sa.String(length=255), nullable=True),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id"),
    )
    op.create_table(
        "cs_knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("freshness_status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "kind", "external_id", name="uq_cs_knowledge_source_external"),
    )
    op.create_index("ix_cs_knowledge_sources_workspace_id", "cs_knowledge_sources", ["workspace_id"])
    op.create_index("ix_cs_knowledge_sources_kind", "cs_knowledge_sources", ["kind"])
    op.create_table(
        "cs_knowledge_settings",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("no_answer_policy", sa.String(length=32), nullable=False),
        sa.Column("no_answer_message", sa.Text(), nullable=False),
        sa.Column("minimum_score", sa.Float(), nullable=False),
        sa.Column("freshness_days", sa.Integer(), nullable=False),
        sa.Column("citations_required", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id"),
    )
    op.create_table(
        "cs_knowledge_evaluation_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cs_knowledge_evaluation_questions_workspace_id",
        "cs_knowledge_evaluation_questions",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cs_knowledge_evaluation_questions_workspace_id", table_name="cs_knowledge_evaluation_questions")
    op.drop_table("cs_knowledge_evaluation_questions")
    op.drop_table("cs_knowledge_settings")
    op.drop_index("ix_cs_knowledge_sources_kind", table_name="cs_knowledge_sources")
    op.drop_index("ix_cs_knowledge_sources_workspace_id", table_name="cs_knowledge_sources")
    op.drop_table("cs_knowledge_sources")
    op.drop_table("cs_email_identities")
