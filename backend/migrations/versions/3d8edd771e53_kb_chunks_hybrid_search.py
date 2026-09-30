"""kb chunks hybrid search

Revision ID: 3d8edd771e53
Revises: 94c08d5d1898
Create Date: 2026-02-11 12:07:49.862125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d8edd771e53'
down_revision: Union[str, Sequence[str], None] = '94c08d5d1898'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.execute("""
    CREATE TABLE IF NOT EXISTS kb_chunks (
      id BIGSERIAL PRIMARY KEY,
      user_id UUID NOT NULL,
      doc_id TEXT NOT NULL,

      source TEXT,
      filename TEXT,
      mime_type TEXT,

      page INT,
      chunk_index INT NOT NULL,

      title TEXT,
      content TEXT NOT NULL,

      content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(content,''))) STORED,
      embedding vector(1536),

      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

    op.execute("CREATE INDEX IF NOT EXISTS kb_chunks_user_doc_idx ON kb_chunks (user_id, doc_id);")
    op.execute("CREATE INDEX IF NOT EXISTS kb_chunks_tsv_idx ON kb_chunks USING GIN (content_tsv);")
    op.execute("""
      CREATE INDEX IF NOT EXISTS kb_chunks_vec_idx
      ON kb_chunks
      USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 100);
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS kb_chunks CASCADE;")
