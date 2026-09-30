from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings import embed_texts


DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 120


@dataclass(frozen=True)
class KnowledgeDocument:
    text: str
    source: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    page: int | None = None
    title: str | None = None
    metadata: dict[str, Any] | None = None


def chunk_text(
    text_value: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    text_value = (text_value or "").strip()

    if not text_value:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0

    while start < len(text_value):
        end = min(start + chunk_size, len(text_value))
        chunk = text_value[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text_value):
            break

        start = end - chunk_overlap

    return chunks


def _vector_to_pgvector_str(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"


async def upsert_document_chunks(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    doc_id: str,
    documents: list[KnowledgeDocument],
    replace_existing: bool = True,
) -> int:
    if not documents:
        return 0

    chunks_to_insert: list[dict[str, Any]] = []

    for document in documents:
        chunks = chunk_text(document.text)

        for index, chunk in enumerate(chunks):
            chunks_to_insert.append(
                {
                    "content": chunk,
                    "source": document.source,
                    "filename": document.filename,
                    "mime_type": document.mime_type,
                    "page": document.page,
                    "title": document.title,
                    "chunk_index": index,
                }
            )

    if not chunks_to_insert:
        return 0

    embeddings = await embed_texts([item["content"] for item in chunks_to_insert])

    if len(embeddings) != len(chunks_to_insert):
        raise RuntimeError("Embedding count does not match chunk count")

    if replace_existing:
        await db.execute(
            text(
                """
                DELETE FROM kb_chunks
                WHERE user_id = :user_id
                  AND doc_id = :doc_id
                """
            ),
            {
                "user_id": user_id,
                "doc_id": doc_id,
            },
        )

    insert_sql = text(
        """
        INSERT INTO kb_chunks (
            user_id,
            doc_id,
            source,
            filename,
            mime_type,
            page,
            chunk_index,
            title,
            content,
            embedding
        )
        VALUES (
            :user_id,
            :doc_id,
            :source,
            :filename,
            :mime_type,
            :page,
            :chunk_index,
            :title,
            :content,
            (:embedding)::vector
        )
        """
    )

    for item, vector in zip(chunks_to_insert, embeddings):
        await db.execute(
            insert_sql,
            {
                "user_id": user_id,
                "doc_id": doc_id,
                "source": item["source"],
                "filename": item["filename"],
                "mime_type": item["mime_type"],
                "page": item["page"],
                "chunk_index": item["chunk_index"],
                "title": item["title"],
                "content": item["content"],
                "embedding": _vector_to_pgvector_str(vector),
            },
        )

    await db.commit()

    return len(chunks_to_insert)
