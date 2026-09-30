import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_reply_quality_dashboard_endpoint():
    user = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/customer-service/analytics/reply-quality/dashboard"
            )

            assert response.status_code == 200

            data = response.json()

            assert "best_reply_types" in data
            assert "worst_reply_types" in data
            assert "best_intents" in data
            assert "worst_intents" in data

    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
