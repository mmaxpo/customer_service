from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_shipping_tracking_found_and_cached():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/customer-service/shipping/track",
                json={
                    "provider": "DHL",
                    "tracking_number": "TRACK123",
                },
            )

            assert response.status_code == 200

            data = response.json()

            assert data["provider"] == "dhl"
            assert data["tracking_number"] == "TRACK123"
            assert data["status"] == "in_transit"
            assert (
                data["payload"]["last_event"]["description"] == "Package is in transit"
            )

            cached = await client.post(
                "/customer-service/shipping/track",
                json={
                    "provider": "dhl",
                    "tracking_number": "TRACK123",
                },
            )

            assert cached.status_code == 200
            assert cached.json()["id"] == data["id"]

    finally:
        app.dependency_overrides.pop(get_current_user, None)
