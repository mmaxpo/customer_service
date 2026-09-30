from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings import embed_query
from app.services.knowledge_ingest import _vector_to_pgvector_str


def _normalize_fts(score: float | None) -> float:
    if score is None:
        return 0.0

    return max(0.0, min(1.0, float(score) / 0.2))


async def fts_search(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query: str,
    k: int = 12,
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                doc_id,
                source,
                filename,
                mime_type,
                page,
                chunk_index,
                title,
                content,
                ts_rank_cd(content_tsv, websearch_to_tsquery('english', :query)) AS score_fts
            FROM kb_chunks
            WHERE user_id = :user_id
              AND content_tsv @@ websearch_to_tsquery('english', :query)
            ORDER BY score_fts DESC
            LIMIT :k
            """
        ),
        {
            "user_id": user_id,
            "query": query,
            "k": k,
        },
    )

    return [dict(row) for row in result.mappings().all()]


async def vector_search(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query: str,
    k: int = 12,
) -> list[dict[str, Any]]:
    vector = await embed_query(query)

    result = await db.execute(
        text(
            """
            SELECT
                id,
                doc_id,
                source,
                filename,
                mime_type,
                page,
                chunk_index,
                title,
                content,
                1 - (embedding <=> (:embedding)::vector) AS score_vec
            FROM kb_chunks
            WHERE user_id = :user_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> (:embedding)::vector
            LIMIT :k
            """
        ),
        {
            "user_id": user_id,
            "embedding": _vector_to_pgvector_str(vector),
            "k": k,
        },
    )

    return [dict(row) for row in result.mappings().all()]


def merge_results(
    fts: list[dict[str, Any]],
    vec: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[Any, dict[str, Any]] = {}

    for row in fts:
        row = dict(row)
        row["score_fts_norm"] = _normalize_fts(row.get("score_fts"))
        row["score_vec_norm"] = 0.0
        merged[row["id"]] = row

    for row in vec:
        row = dict(row)
        current = merged.get(row["id"])

        if current is None:
            row["score_fts_norm"] = 0.0
            row["score_vec_norm"] = max(
                0.0, min(1.0, float(row.get("score_vec") or 0.0))
            )
            merged[row["id"]] = row
        else:
            current["score_vec"] = row.get("score_vec")
            current["score_vec_norm"] = max(
                0.0,
                min(1.0, float(row.get("score_vec") or 0.0)),
            )

    results = list(merged.values())

    for row in results:
        row["score_hybrid"] = 0.45 * row.get("score_fts_norm", 0.0) + 0.55 * row.get(
            "score_vec_norm", 0.0
        )

    results.sort(key=lambda x: x.get("score_hybrid", 0.0), reverse=True)

    return results


async def hybrid_retrieve(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    *,
    k_fts: int = 12,
    k_vec: int = 12,
    pre_rerank_top_n: int = 20,
) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return []

    fts = await fts_search(
        db,
        user_id=user_id,
        query=query,
        k=k_fts,
    )

    vec = await vector_search(
        db,
        user_id=user_id,
        query=query,
        k=k_vec,
    )

    return merge_results(fts, vec)[:pre_rerank_top_n]
