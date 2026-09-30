from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "phase2-intelligence@example.com"


@pytest.mark.asyncio
async def test_conversation_intelligence_analyzes_and_persists():
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
                        "name": "Phase 2 User",
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
                        "subject": "Damaged order",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "My order arrived damaged and I need a refund urgently.",
                },
            )

            analyze_response = await client.post(
                f"/customer-service/conversations/{conversation['id']}/intelligence/analyze",
                json={},
            )

            assert analyze_response.status_code == 200

            insight = analyze_response.json()

            assert insight["conversation_id"] == conversation["id"]
            assert insight["intent"] == "refund_request"
            assert insight["sentiment"] == "negative"
            assert insight["urgency"] == "high"
            assert insight["risks"]["churn_risk"] in {"medium", "high"}
            assert insight["opportunities"]["save_customer"] is True
            assert insight["source"] == "rule"

            list_response = await client.get(
                f"/customer-service/conversations/{conversation['id']}/intelligence"
            )

            assert list_response.status_code == 200
            assert len(list_response.json()) >= 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_conversation_intelligence_returns_404_for_other_user_conversation():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/customer-service/conversations/{uuid4()}/intelligence/analyze",
                json={},
            )

            assert response.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
