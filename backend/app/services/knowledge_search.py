from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_retrieval import hybrid_retrieve
from app.services.rerank_local import LocalReranker


async def hybrid_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    *,
    final_k: int = 8,
    reranker: LocalReranker | None = None,
) -> list[dict[str, Any]]:
    candidates = await hybrid_retrieve(
        db=db,
        user_id=user_id,
        query=query,
    )

    if reranker is not None and candidates:
        passages = [(candidate.get("content") or "")[:1500] for candidate in candidates]
        scores = reranker.score(query, passages, batch_size=16)

        for candidate, score in zip(candidates, scores):
            candidate["score_rerank"] = float(score)

        candidates.sort(
            key=lambda candidate: candidate.get("score_rerank", -1e9),
            reverse=True,
        )

    return candidates[:final_k]
