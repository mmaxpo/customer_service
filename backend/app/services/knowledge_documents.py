from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def delete_knowledge_document(
    db: AsyncSession,
    *,
    user_id: Any,
    doc_id: str,
) -> None:
    """
    Delete every chunk belonging to one user's knowledge document.

    Persistence and transaction completion are owned outside the
    HTTP adapter.
    """

    await db.execute(
        text(
            """
            DELETE FROM kb_chunks
            WHERE user_id = :uid
              AND doc_id = :doc
            """
        ),
        {
            "uid": user_id,
            "doc": doc_id,
        },
    )

    await db.commit()


async def list_knowledge_documents(
    db: AsyncSession,
    *,
    user_id: Any,
) -> list[dict[str, Any]]:
    """
    Return one summary row per document owned by the user.
    """

    result = await db.execute(
        text(
            """
            SELECT
                doc_id,
                max(updated_at) AS updated_at,
                count(*) AS chunks
            FROM kb_chunks
            WHERE user_id = :uid
            GROUP BY doc_id
            ORDER BY updated_at DESC
            """
        ),
        {
            "uid": user_id,
        },
    )

    return [dict(row) for row in result.mappings().all()]


__all__ = [
    "delete_knowledge_document",
    "list_knowledge_documents",
]
