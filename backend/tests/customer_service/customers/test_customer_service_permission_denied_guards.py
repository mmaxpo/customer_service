import pytest

from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_customer_service_agents_requires_authentication_permission_denied():

    app.dependency_overrides.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/customer-service/agents")

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_customer_service_workflow_templates_requires_authentication_permission_denied():

    app.dependency_overrides.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/customer-service/workflow-templates")

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_customer_service_event_subscriptions_requires_authentication_permission_denied():

    app.dependency_overrides.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/customer-service/event-subscriptions")

    assert response.status_code in {401, 403}
