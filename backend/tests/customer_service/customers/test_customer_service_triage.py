from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user
from app.domains.customer_service.services.triage import AutoTriageService


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "triage@example.com"


@pytest.mark.asyncio
async def test_auto_triage():
    result = await AutoTriageService().classify(
        "My order arrived damaged and I need refund urgently"
    )

    assert result.intent == "refund_request"
    assert "refund" in result.tags
    assert "damaged_item" in result.tags
    assert result.priority == "HIGH"


@pytest.mark.asyncio
async def test_triage_creates_tags():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Triage User",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+49123456",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "chat",
                        "subject": "Triage test",
                    },
                )
            ).json()

            result = await client.post(
                f"/customer-service/conversations/{conversation['id']}/triage",
                json={"message": "Refund my damaged order urgently"},
            )

            assert result.status_code == 200

            tags = await client.get(
                f"/customer-service/conversations/{conversation['id']}/tags/"
            )

            names = [t["name"] for t in tags.json()]

            assert "refund" in names
            assert "damaged_item" in names

    finally:
        app.dependency_overrides.pop(get_current_user, None)
