from __future__ import annotations

import uuid
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.knowledge_search import hybrid_search


class KnowledgeService:
    def __init__(self, session_factory: async_sessionmaker):
        self.SessionLocal = session_factory

    async def search(
        self,
        user_id: uuid.UUID,
        query: str,
        k: int = 6,
        reranker=None,
    ) -> Dict[str, Any]:
        k = max(1, min(int(k), 20))

        async with self.SessionLocal() as db:
            results = await hybrid_search(
                db=db,
                user_id=user_id,
                query=query,
                final_k=k,
                reranker=reranker,
            )

        return {
            "ok": True,
            "query": query,
            "results": results,
        }

    async def list_docs(self, user_id: uuid.UUID):
        async with self.SessionLocal() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            """
                            SELECT doc_id,
                                   max(updated_at) AS updated_at,
                                   count(*) AS chunks
                            FROM kb_chunks
                            WHERE user_id = :uid
                            GROUP BY doc_id
                            ORDER BY updated_at DESC
                            """
                        ),
                        {"uid": user_id},
                    )
                )
                .mappings()
                .all()
            )

        return {"ok": True, "docs": [dict(r) for r in rows]}

    async def delete_doc(self, user_id: uuid.UUID, doc_id: str):
        async with self.SessionLocal() as db:
            await db.execute(
                text(
                    "DELETE FROM kb_chunks WHERE user_id=:uid AND doc_id=:doc"
                ),
                {"uid": user_id, "doc": doc_id},
            )
            await db.commit()

        return {"ok": True, "doc_id": doc_id}