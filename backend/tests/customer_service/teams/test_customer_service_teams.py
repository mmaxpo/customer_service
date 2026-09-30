from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "teams@example.com"
        self.customer_service_role = "owner"


async def _create_agent(client, name="Team Agent"):
    response = await client.post(
        "/customer-service/agents",
        json={
            "agent_user_id": str(uuid4()),
            "display_name": name,
            "email": f"{uuid4()}@example.com",
            "skills": ["shipping"],
            "channels": ["whatsapp"],
            "languages": ["en"],
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_create_team_add_member_get_detail_and_remove_member():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            agent = await _create_agent(client, "Shipping Agent")

            team = await client.post(
                "/customer-service/teams",
                json={
                    "name": "Shipping Team",
                    "description": "Handles delivery and tracking questions",
                },
            )
            assert team.status_code == 200
            team_body = team.json()
            assert team_body["name"] == "Shipping Team"

            member = await client.post(
                f"/customer-service/teams/{team_body['id']}/members",
                json={"agent_id": agent["id"]},
            )
            assert member.status_code == 200
            assert member.json()["agent_id"] == agent["id"]

            detail = await client.get(f"/customer-service/teams/{team_body['id']}")
            assert detail.status_code == 200
            assert detail.json()["members"][0]["id"] == agent["id"]

            removed = await client.delete(
                f"/customer-service/teams/{team_body['id']}/members/{agent['id']}"
            )
            assert removed.status_code == 204

            detail = await client.get(f"/customer-service/teams/{team_body['id']}")
            assert detail.status_code == 200
            assert detail.json()["members"] == []

            deleted = await client.delete(f"/customer-service/teams/{team_body['id']}")
            assert deleted.status_code == 204
    finally:
        app.dependency_overrides.pop(get_current_user, None)
