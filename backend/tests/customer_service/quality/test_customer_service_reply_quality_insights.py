from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


async def _create_conversation(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Insights Customer",
                "email": f"{uuid4()}@test.com",
                "phone": "111",
            },
        )
    ).json()

    return (
        await client.post(
            "/customer-service/conversations/",
            json={
                "customer_id": customer["id"],
                "channel": "chat",
                "subject": "reply quality",
            },
        )
    ).json()


@pytest.mark.asyncio
async def test_reply_quality_insights_aggregates_acceptance_edit_and_rejection_rates():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            conversation = await _create_conversation(client)

            for outcome in [
                "accepted_without_edit",
                "accepted_with_edit",
                "rejected",
            ]:
                response = await client.post(
                    f"/customer-service/conversations/{conversation['id']}/reply-quality",
                    json={
                        "conversation_id": conversation["id"],
                        "outcome": outcome,
                        "draft_body": "Original AI reply",
                        "final_body": (
                            "Edited final AI reply"
                            if outcome == "accepted_with_edit"
                            else "Original AI reply"
                        ),
                    },
                )
                assert response.status_code == 200

            insights = await client.get(
                "/customer-service/analytics/reply-quality/insights"
            )

            assert insights.status_code == 200

            data = insights.json()

            assert data["total_reviews"] == 3
            assert data["accepted_without_edit"] == 1
            assert data["accepted_with_edit"] == 1
            assert data["rejected"] == 1
            assert data["acceptance_rate"] == 0.6667
            assert data["edit_rate"] == 0.3333
            assert data["rejection_rate"] == 0.3333
            assert data["average_score"] is not None
            assert data["average_edit_distance"] is not None

    finally:
        app.dependency_overrides.pop(get_current_user, None)
