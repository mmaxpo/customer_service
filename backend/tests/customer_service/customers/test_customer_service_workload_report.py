from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_workload_report_endpoint_returns_expected_shape():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/customer-service/analytics/workload-report")

            assert response.status_code == 200

            payload = response.json()

            assert "queues" in payload
            assert "teams" in payload
            assert "agents" in payload

            assert isinstance(payload["queues"], list)
            assert isinstance(payload["teams"], list)
            assert isinstance(payload["agents"], list)

    finally:
        app.dependency_overrides.pop(get_current_user, None)
