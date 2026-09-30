from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.role = "owner"


@pytest.mark.asyncio
async def test_seed_shopify_event_subscriptions_is_idempotent_and_template_backed():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/customer-service/event-subscriptions/seed-shopify"
            )

            assert first.status_code == 200

            first_data = first.json()

            assert first_data["created_count"] == 4
            assert first_data["existing_count"] == 0

            created = first_data["created"]

            assert all(item["workflow_template_id"] for item in created)
            assert all(item["workflow_json"] is None for item in created)
            assert all(item["is_active"] is True for item in created)
            filter_keywords = [
                keyword
                for item in created
                for keyword in item["filters"].get("keywords", [])
            ]

            assert "refund" in filter_keywords
            assert "cancel" in filter_keywords
            assert "damaged" in filter_keywords
            assert "where is my order" in filter_keywords

            listed = await client.get("/customer-service/event-subscriptions")

            assert listed.status_code == 200
            assert len(listed.json()) >= 4

            second = await client.post(
                "/customer-service/event-subscriptions/seed-shopify"
            )

            assert second.status_code == 200

            second_data = second.json()

            assert second_data["created_count"] == 0
            assert second_data["existing_count"] == 4

    finally:
        app.dependency_overrides.pop(get_current_user, None)
