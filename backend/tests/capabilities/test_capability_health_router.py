from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_health_override_and_reads_are_user_scoped():
    current_user_id = uuid4()
    other_user_id = uuid4()

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(current_user_id)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.patch(
                "/capabilities/health/override",
                json={
                    "tenant_id": "tenant_1",
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": "shopify",
                    "provider_ref": (
                        "shopify.get_order"
                    ),
                    "override_state": "unhealthy",
                    "reason": "operator maintenance",
                },
            )

            assert created.status_code == 200
            assert (
                created.json()["current_state"]
                == "healthy"
            )
            assert (
                created.json()["effective_state"]
                == "unhealthy"
            )

            states = await client.get(
                "/capabilities/health/states",
                params={
                    "tenant_id": "tenant_1",
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": "shopify",
                },
            )

            assert states.status_code == 200
            assert len(states.json()["items"]) == 1

            # Switching authenticated ownership cannot see the row.
            app.dependency_overrides[
                get_current_user
            ] = lambda: FakeUser(other_user_id)

            hidden = await client.get(
                "/capabilities/health/states",
                params={
                    "tenant_id": "tenant_1",
                    "provider_id": "shopify",
                },
            )

            assert hidden.status_code == 200
            assert hidden.json()["items"] == []
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_health_override_can_be_cleared():
    user_id = uuid4()

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(user_id)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.patch(
                "/capabilities/health/override",
                json={
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": "shopify",
                    "override_state": "degraded",
                    "reason": "temporary",
                },
            )

            cleared = await client.delete(
                "/capabilities/health/override",
                params={
                    "capability_id": (
                        "ecommerce.orders.get"
                    ),
                    "provider_id": "shopify",
                },
            )

            assert cleared.status_code == 200
            assert (
                cleared.json()["override_active"]
                is False
            )
            assert (
                cleared.json()["effective_state"]
                == cleared.json()["current_state"]
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
