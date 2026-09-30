"""add reply quality fields

Revision ID: qr1a000000001
Revises: a3e14571c969
Create Date: 2026-05-29 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "qr1a000000001"
down_revision: Union[str, Sequence[str], None] = "a3e14571c969"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cs_quality_reviews", sa.Column("reply_message_id", sa.UUID(), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("review_type", sa.String(length=50), nullable=False, server_default="ai_reply"))
    op.add_column("cs_quality_reviews", sa.Column("outcome", sa.String(length=50), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("accuracy_score", sa.Float(), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("relevance_score", sa.Float(), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("tone_score", sa.Float(), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("draft_body", sa.Text(), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("final_body", sa.Text(), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("edit_distance", sa.Integer(), nullable=True))
    op.add_column("cs_quality_reviews", sa.Column("reviewer_id", sa.UUID(), nullable=True))

    op.create_index("ix_cs_quality_reviews_reply_message_id", "cs_quality_reviews", ["reply_message_id"])
    op.create_index("ix_cs_quality_reviews_review_type", "cs_quality_reviews", ["review_type"])
    op.create_index("ix_cs_quality_reviews_outcome", "cs_quality_reviews", ["outcome"])
    op.create_index("ix_cs_quality_reviews_reviewer_id", "cs_quality_reviews", ["reviewer_id"])
    op.create_index("ix_cs_quality_reviews_user_review_type", "cs_quality_reviews", ["user_id", "review_type"])
    op.create_index("ix_cs_quality_reviews_user_outcome", "cs_quality_reviews", ["user_id", "outcome"])
    op.create_index("ix_cs_quality_reviews_conversation_review_type", "cs_quality_reviews", ["conversation_id", "review_type"])


def downgrade() -> None:
    op.drop_index("ix_cs_quality_reviews_conversation_review_type", table_name="cs_quality_reviews")
    op.drop_index("ix_cs_quality_reviews_user_outcome", table_name="cs_quality_reviews")
    op.drop_index("ix_cs_quality_reviews_user_review_type", table_name="cs_quality_reviews")
    op.drop_index("ix_cs_quality_reviews_reviewer_id", table_name="cs_quality_reviews")
    op.drop_index("ix_cs_quality_reviews_outcome", table_name="cs_quality_reviews")
    op.drop_index("ix_cs_quality_reviews_review_type", table_name="cs_quality_reviews")
    op.drop_index("ix_cs_quality_reviews_reply_message_id", table_name="cs_quality_reviews")

    op.drop_column("cs_quality_reviews", "reviewer_id")
    op.drop_column("cs_quality_reviews", "edit_distance")
    op.drop_column("cs_quality_reviews", "final_body")
    op.drop_column("cs_quality_reviews", "draft_body")
    op.drop_column("cs_quality_reviews", "tone_score")
    op.drop_column("cs_quality_reviews", "relevance_score")
    op.drop_column("cs_quality_reviews", "accuracy_score")
    op.drop_column("cs_quality_reviews", "outcome")
    op.drop_column("cs_quality_reviews", "review_type")
    op.drop_column("cs_quality_reviews", "reply_message_id")
