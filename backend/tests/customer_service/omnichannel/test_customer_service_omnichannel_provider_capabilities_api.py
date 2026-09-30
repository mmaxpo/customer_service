from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    id = uuid4()


@pytest.mark.asyncio
async def test_provider_capabilities_api_hides_unfinished_channels():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/customer-service/omnichannel/providers/capabilities"
            )

        assert response.status_code == 200

        assert response.json() == []
    finally:
        app.dependency_overrides.clear()
