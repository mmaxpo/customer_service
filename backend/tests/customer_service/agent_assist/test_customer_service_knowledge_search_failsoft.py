from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domains.customer_service.services.knowledge import (
    CustomerServiceKnowledgeService,
)


@pytest.mark.asyncio
async def test_knowledge_search_returns_no_context_when_embedding_provider_fails(
    monkeypatch,
):
    service = CustomerServiceKnowledgeService(db=object())

    async def fake_settings(*, workspace_id, persist=False):
        return SimpleNamespace(
            minimum_score=0.72,
            no_answer_policy="handoff",
            no_answer_message="A support agent will review this request.",
        )

    async def broken_search(**kwargs):
        raise RuntimeError("embedding provider unavailable")

    monkeypatch.setattr(service, "get_settings", fake_settings)
    monkeypatch.setattr(
        "app.domains.customer_service.services.knowledge.hybrid_search",
        broken_search,
    )

    result = await service.search_context(
        user_id=uuid4(),
        query="Where is my order?",
        k=3,
    )

    assert result["answered"] is False
    assert result["context"] == ""
    assert result["hits"] == []
    assert result["no_answer_policy"] == "handoff"
