from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_suggested_actions_do_not_fail_when_knowledge_search_fails(monkeypatch):
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    async def broken_search_context(self, *, user_id, query, k=5):
        raise RuntimeError("embedding provider unavailable")

    monkeypatch.setattr(
        "app.domains.customer_service.services.suggested_actions.CustomerServiceKnowledgeService.search_context",
        broken_search_context,
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
                        "name": "Failsoft User",
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
                        "subject": "urgent refund",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "refund damaged urgent",
                },
            )

            response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/suggested-actions/generate"
            )

            assert response.status_code == 200

            action_types = {item["action_type"] for item in response.json()}

            assert "refund" in action_types
            assert "assign" in action_types

    finally:
        app.dependency_overrides.pop(get_current_user, None)
