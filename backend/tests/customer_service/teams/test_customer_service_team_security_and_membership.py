from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.customer_service_role = "owner"


async def _create_team(client, name="Support Team"):
    response = await client.post(
        "/customer-service/teams",
        json={
            "name": name,
            "description": "Customer support team",
            "is_active": True,
        },
    )
    assert response.status_code == 200
    return response.json()


async def _create_agent(client, email=None):
    response = await client.post(
        "/customer-service/agents",
        json={
            "agent_user_id": str(uuid4()),
            "display_name": "Support Agent",
            "email": email or f"{uuid4()}@example.com",
            "status": "active",
            "availability": "available",
            "skills": ["refunds", "shipping"],
            "channels": ["chat"],
            "languages": ["en"],
            "max_open_tickets": 5,
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


@pytest.mark.asyncio
async def test_team_lifecycle_is_user_scoped():
    user_a = FakeUser()
    user_b = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            app.dependency_overrides[get_current_user] = lambda: user_b

            get_response = await client.get(f"/customer-service/teams/{team['id']}")
            assert get_response.status_code == 404

            update_response = await client.patch(
                f"/customer-service/teams/{team['id']}",
                json={"name": "Attack Team"},
            )
            assert update_response.status_code == 404

            delete_response = await client.delete(
                f"/customer-service/teams/{team['id']}"
            )
            assert delete_response.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_team_membership_is_idempotent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)
            agent = await _create_agent(client)

            first = await client.post(
                f"/customer-service/teams/{team['id']}/members",
                json={
                    "agent_id": agent["id"],
                    "role": "member",
                },
            )
            assert first.status_code == 200

            second = await client.post(
                f"/customer-service/teams/{team['id']}/members",
                json={
                    "agent_id": agent["id"],
                    "role": "member",
                },
            )
            assert second.status_code == 200
            assert second.json()["id"] == first.json()["id"]

            detail = await client.get(f"/customer-service/teams/{team['id']}")
            assert detail.status_code == 200
            assert len(detail.json()["members"]) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
