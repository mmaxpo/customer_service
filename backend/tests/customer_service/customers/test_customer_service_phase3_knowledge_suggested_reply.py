from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_suggested_actions_include_knowledge_reply(monkeypatch):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    async def fake_search_context(self, *, user_id, query, k=5):
        assert user_id == user.id

        return {
            "query": query,
            "context": "[1] Refund Policy\\nRefunds are processed within 5 business days.",
            "hits": [
                {
                    "doc_id": "refund-doc",
                    "title": "Refund Policy",
                    "filename": "refund.md",
                    "content": "Refunds are processed within 5 business days.",
                    "score": 0.91,
                    "source": "manual",
                    "page": None,
                    "chunk_index": 0,
                }
            ],
        }

    monkeypatch.setattr(
        "app.domains.customer_service.services.suggested_actions.CustomerServiceKnowledgeService.search_context",
        fake_search_context,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Knowledge Reply User",
                        "email": f"{uuid4()}@test.com",
                        "phone": "111",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "chat",
                        "subject": "refund policy",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "How long does a refund take?",
                },
            )

            response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )

            assert response.status_code == 200

            actions = response.json()
            reply = next(a for a in actions if a["action_type"] == "reply")

            assert reply["source"] == "knowledge"
            assert (
                "Refunds are processed within 5 business days"
                in reply["payload"]["body"]
            )
            assert reply["payload"]["knowledge_hits"][0]["doc_id"] == "refund-doc"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
