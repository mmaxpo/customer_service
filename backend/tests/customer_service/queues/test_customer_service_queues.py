from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "queues@example.com"
        self.customer_service_role = "owner"


async def _create_team(client):
    team = await client.post(
        "/customer-service/teams",
        json={
            "name": f"Queue Team {uuid4()}",
            "description": "Queue owning team",
        },
    )
    assert team.status_code == 200
    return team.json()


@pytest.mark.asyncio
async def test_create_list_update_delete_customer_service_queue():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            created = await client.post(
                "/customer-service/queues",
                json={
                    "name": "VIP Shipping Queue",
                    "description": "High value shipping tickets",
                    "team_id": team["id"],
                    "channel": "whatsapp",
                    "intent": "shipping",
                    "priority": "high",
                    "priority_rank": 10,
                    "is_default": False,
                    "filters": {"keywords": ["vip", "urgent"]},
                },
            )

            assert created.status_code == 200
            body = created.json()
            assert body["name"] == "VIP Shipping Queue"
            assert body["team_id"] == team["id"]
            assert body["priority_rank"] == 10

            listed = await client.get("/customer-service/queues")
            assert listed.status_code == 200
            assert any(item["id"] == body["id"] for item in listed.json())

            fetched = await client.get(f"/customer-service/queues/{body['id']}")
            assert fetched.status_code == 200
            assert fetched.json()["channel"] == "whatsapp"

            updated = await client.patch(
                f"/customer-service/queues/{body['id']}",
                json={
                    "name": "Updated VIP Shipping Queue",
                    "priority_rank": 5,
                    "is_default": True,
                },
            )

            assert updated.status_code == 200
            assert updated.json()["name"] == "Updated VIP Shipping Queue"
            assert updated.json()["priority_rank"] == 5
            assert updated.json()["is_default"] is True

            active = await client.get(
                "/customer-service/queues",
                params={"active_only": True},
            )
            assert active.status_code == 200
            assert any(item["id"] == body["id"] for item in active.json())

            deleted = await client.delete(f"/customer-service/queues/{body['id']}")
            assert deleted.status_code == 204

            missing = await client.get(f"/customer-service/queues/{body['id']}")
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_delete_team_preserves_queue_and_clears_team_reference():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            team = await _create_team(client)

            created = await client.post(
                "/customer-service/queues",
                json={
                    "name": f"Detached Queue {uuid4()}",
                    "description": ("Queue must survive deletion of its owning team"),
                    "team_id": team["id"],
                    "channel": "email",
                    "priority_rank": 20,
                },
            )

            assert created.status_code == 200
            queue = created.json()
            assert queue["team_id"] == team["id"]

            deleted_team = await client.delete(f"/customer-service/teams/{team['id']}")

            assert deleted_team.status_code == 204

            missing_team = await client.get(f"/customer-service/teams/{team['id']}")
            assert missing_team.status_code == 404

            surviving_queue = await client.get(
                f"/customer-service/queues/{queue['id']}"
            )

            assert surviving_queue.status_code == 200
            assert surviving_queue.json()["id"] == queue["id"]
            assert surviving_queue.json()["team_id"] is None

            deleted_queue = await client.delete(
                f"/customer-service/queues/{queue['id']}"
            )
            assert deleted_queue.status_code == 204
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
