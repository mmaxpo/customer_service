from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-connections@example.com"


@pytest.mark.asyncio
async def test_omnichannel_channel_connection_create_and_list():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/customer-service/omnichannel/connections",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-connection",
                    "display_name": "Main WhatsApp Business",
                    "config": {"region": "eu"},
                },
            )
            assert created.status_code == 200
            assert created.json()["channel"] == "whatsapp"

            listed = await client.get("/customer-service/omnichannel/connections")
            assert listed.status_code == 200
            assert any(
                item["external_account_id"] == "wa-business-connection"
                for item in listed.json()
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
