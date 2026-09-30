from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.knowledge_documents import (
    delete_knowledge_document,
    list_knowledge_documents,
)


@pytest.mark.asyncio
async def test_delete_knowledge_document_executes_scoped_delete_and_commits():
    db = SimpleNamespace(
        execute=AsyncMock(),
        commit=AsyncMock(),
    )

    await delete_knowledge_document(
        db,
        user_id="user-123",
        doc_id="doc-456",
    )

    db.execute.assert_awaited_once()

    statement, params = db.execute.await_args.args

    sql = " ".join(str(statement).split())

    assert "DELETE FROM kb_chunks" in sql

    assert "user_id = :uid" in sql

    assert "doc_id = :doc" in sql

    assert params == {
        "uid": "user-123",
        "doc": "doc-456",
    }

    db.commit.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_list_knowledge_documents_is_user_scoped_and_returns_mappings():
    rows = [
        {
            "doc_id": "doc-a",
            "updated_at": "2026-08-18",
            "chunks": 3,
        },
        {
            "doc_id": "doc-b",
            "updated_at": "2026-08-17",
            "chunks": 2,
        },
    ]

    mappings = SimpleNamespace(all=lambda: rows)

    result_proxy = SimpleNamespace(mappings=lambda: mappings)

    db = SimpleNamespace(execute=AsyncMock(return_value=result_proxy))

    result = await list_knowledge_documents(
        db,
        user_id="user-123",
    )

    assert result == rows

    db.execute.assert_awaited_once()

    statement, params = db.execute.await_args.args

    sql = " ".join(str(statement).split())

    assert "FROM kb_chunks" in sql
    assert "WHERE user_id = :uid" in sql
    assert "GROUP BY doc_id" in sql
    assert "ORDER BY updated_at DESC" in sql

    assert params == {
        "uid": "user-123",
    }
