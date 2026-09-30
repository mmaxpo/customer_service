from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_event_subscription_lifecycle_is_user_scoped():
    user_a = FakeUser()
    user_b = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seeded = await client.post(
                "/customer-service/event-subscriptions/seed-shopify"
            )
            assert seeded.status_code == 200

            subscription_id = seeded.json()["created"][0]["id"]

            app.dependency_overrides[get_current_user] = lambda: user_b

            get_response = await client.get(
                f"/customer-service/event-subscriptions/{subscription_id}"
            )
            assert get_response.status_code == 404

            update_response = await client.patch(
                f"/customer-service/event-subscriptions/{subscription_id}",
                json={"name": "User B Attack"},
            )
            assert update_response.status_code == 404

            disable_response = await client.post(
                f"/customer-service/event-subscriptions/{subscription_id}/disable"
            )
            assert disable_response.status_code == 404

            enable_response = await client.post(
                f"/customer-service/event-subscriptions/{subscription_id}/enable"
            )
            assert enable_response.status_code == 404

            delete_response = await client.delete(
                f"/customer-service/event-subscriptions/{subscription_id}"
            )
            assert delete_response.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)
