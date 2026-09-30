from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_search import hybrid_search
from app.tools.common.logging import tool_span
from app.tools.common.types import ToolResult


class KnowledgeSearchService:
    async def search(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        *,
        k: int = 8,
    ) -> ToolResult:
        with tool_span("knowledge_search", query=query, k=k):
            hits = await hybrid_search(
                db=db,
                user_id=user_id,
                query=query,
                final_k=k,
                reranker=None,
            )

        lines = []

        for index, hit in enumerate(hits, start=1):
            title = (
                hit.get("title")
                or hit.get("filename")
                or hit.get("doc_id")
                or "Knowledge"
            )

            score = (
                hit.get("score_rerank")
                or hit.get("score_hybrid")
                or hit.get("score_vec")
                or hit.get("score_fts")
            )

            content = (hit.get("content") or "")[:1200]

            lines.append(
                f"{index}. {title} (score={score})\n"
                f"doc_id={hit.get('doc_id')} chunk={hit.get('chunk_index')} page={hit.get('page')}\n"
                f"{content}"
            )

        return ToolResult(
            content="\n\n---\n\n".join(lines).strip() or "NO_HITS",
            artifact={
                "query": query,
                "k": k,
                "hits": hits,
            },
        )
