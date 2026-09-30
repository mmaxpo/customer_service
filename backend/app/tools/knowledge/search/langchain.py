from __future__ import annotations

import uuid
from typing import Optional
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.knowledge_search import hybrid_search


async def retrieve_impl(
    SessionLocal: async_sessionmaker, reranker, *, query: str, user_id: str, k: int
):
    uid = uuid.UUID(str(user_id))
    k = max(1, min(int(k or 6), 10))

    async with SessionLocal() as db:
        results = await hybrid_search(
            db=db,
            user_id=uid,
            query=query,
            final_k=k,
            reranker=reranker,
        )
    return results


def make_retrieve_tool(SessionLocal: async_sessionmaker, reranker=None):
    @tool(
        response_format="content_and_artifact",
        description="Hybrid search (FTS + vectors + optional rerank) scoped by user_id.",
    )
    async def retrieve(query: str, user_id: Optional[str] = None, k: int = 6):
        try:
            if not user_id:
                return ("USER_ID_REQUIRED", {"ok": False})
            results = await retrieve_impl(
                SessionLocal, reranker, query=query, user_id=user_id, k=k
            )
        except Exception as e:
            return ("RETRIEVE_ERROR", {"ok": False, "error": str(e)})

        if not results:
            return ("NO_MATCH", {"ok": True, "results": []})

        snippets = []
        for r in results:
            s = (r.get("content") or "").strip()
            if len(s) > 600:
                s = s[:600].rsplit(" ", 1)[0] + "…"
            snippets.append(s)

        return ("\n\n".join(snippets), {"ok": True, "results": results})

    return retrieve
