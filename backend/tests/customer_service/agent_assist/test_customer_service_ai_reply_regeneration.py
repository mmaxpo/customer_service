from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.domains.customer_service.services import ai_reply_regeneration


class FakeKnowledgeService:
    def __init__(self, *args, **kwargs):
        pass

    async def search_context(self, *args, **kwargs):
        return []


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_ai_reply_regeneration():
    user = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user
    ai_reply_regeneration.CustomerServiceKnowledgeService = FakeKnowledgeService

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "AI Customer",
                        "email": f"{uuid4()}@test.com",
                        "phone": "123",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "chat",
                        "subject": "refund",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "I need a refund",
                },
            )

            response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/ai-replies/regenerate"
            )

            assert response.status_code == 200

            data = response.json()

            assert data["regenerated"] is True
            assert data["generation"] == 2
            assert data["body"]

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
