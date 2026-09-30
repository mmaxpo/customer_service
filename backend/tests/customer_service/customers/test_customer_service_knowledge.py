from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_customer_service_knowledge_search(monkeypatch):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    async def fake_hybrid_search(db, user_id, query, final_k=8, reranker=None):
        assert user_id == user.id
        assert query == "refund policy"
        assert final_k == 3

        return [
            {
                "doc_id": "refund-doc",
                "title": "Refund Policy",
                "filename": "refund.md",
                "content": "Refunds are processed within 5 business days.",
                "score_hybrid": 0.91,
                "source": "manual",
                "page": None,
                "chunk_index": 0,
            }
        ]

    monkeypatch.setattr(
        "app.domains.customer_service.services.knowledge.hybrid_search",
        fake_hybrid_search,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/knowledge/search",
                json={
                    "query": "refund policy",
                    "k": 3,
                },
            )

            assert response.status_code == 200

            body = response.json()

            assert body["query"] == "refund policy"
            assert "Refunds are processed" in body["context"]
            assert body["hits"][0]["doc_id"] == "refund-doc"
            assert body["hits"][0]["score"] == 0.91

    finally:
        app.dependency_overrides.pop(get_current_user, None)
