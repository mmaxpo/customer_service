"""customer service quality reviews

Revision ID: 7391df9a2134
Revises: d76f18b8b1d3
Create Date: 2026-05-26 20:10:50.094466

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7391df9a2134'
down_revision: Union[str, Sequence[str], None] = 'd76f18b8b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(

        "cs_quality_reviews",

        sa.Column(

            "id",

            postgresql.UUID(as_uuid=True),

            nullable=False,

            primary_key=True,

        ),

        sa.Column(

            "user_id",

            postgresql.UUID(as_uuid=True),

            nullable=False,

        ),

        sa.Column(

            "conversation_id",

            postgresql.UUID(as_uuid=True),

            nullable=False,

        ),

        sa.Column(

            "overall_score",

            sa.Float(),

            nullable=False,

        ),

        sa.Column(

            "scores",

            postgresql.JSONB(astext_type=sa.Text()),

            nullable=True,

        ),

        sa.Column(

            "issues",

            postgresql.JSONB(astext_type=sa.Text()),

            nullable=True,

        ),

        sa.Column(

            "recommendations",

            postgresql.JSONB(astext_type=sa.Text()),

            nullable=True,

        ),

        sa.Column(

            "reviewer_type",

            sa.String(length=50),

            nullable=False,

            server_default="rule",

        ),

        sa.Column(

            "created_at",

            sa.DateTime(timezone=True),

            server_default=sa.func.now(),

        ),

        sa.ForeignKeyConstraint(

            ["conversation_id"],

            ["cs_conversations.id"],

        ),

    )

    op.create_index(

        "ix_cs_quality_reviews_user_id",

        "cs_quality_reviews",

        ["user_id"],

    )

    op.create_index(

        "ix_cs_quality_reviews_conversation_id",

        "cs_quality_reviews",

        ["conversation_id"],

    )

def downgrade() -> None:

    op.drop_index(

        "ix_cs_quality_reviews_conversation_id",

        table_name="cs_quality_reviews",

    )

    op.drop_index(

        "ix_cs_quality_reviews_user_id",

        table_name="cs_quality_reviews",

    )

    op.drop_table(

        "cs_quality_reviews"

    )
