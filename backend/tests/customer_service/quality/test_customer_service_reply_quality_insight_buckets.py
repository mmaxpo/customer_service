from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_reply_quality_insights_bucket_by_reply_type_and_intent():
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
                        "name": "Bucket Customer",
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
                        "subject": "refund",
                    },
                )
            ).json()

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/reply-quality",
                json={
                    "conversation_id": conversation["id"],
                    "outcome": "accepted_without_edit",
                    "draft_body": "Refund reply",
                    "final_body": "Refund reply",
                },
            )

            insights = await client.get(
                "/customer-service/analytics/reply-quality/insights"
            )
            assert insights.status_code == 200

            data = insights.json()

            assert data["by_reply_type"]
            assert data["by_intent"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
