from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "routing-policies@example.com"
        self.customer_service_role = "owner"


@pytest.mark.asyncio
async def test_create_list_update_delete_routing_policy():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        assignee_a = uuid4()
        assignee_b = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "WhatsApp refund routing",
                    "channel": "whatsapp",
                    "intent": "refund",
                    "priority": "high",
                    "strategy": "least_loaded",
                    "candidate_assignee_ids": [str(assignee_a), str(assignee_b)],
                    "filters": {"keywords": ["refund"]},
                },
            )

            assert created.status_code == 200
            body = created.json()
            assert body["name"] == "WhatsApp refund routing"
            assert body["candidate_assignee_ids"] == [str(assignee_a), str(assignee_b)]

            listed = await client.get("/customer-service/routing-policies")
            assert listed.status_code == 200
            assert any(item["id"] == body["id"] for item in listed.json())

            fetched = await client.get(
                f"/customer-service/routing-policies/{body['id']}"
            )
            assert fetched.status_code == 200
            assert fetched.json()["channel"] == "whatsapp"

            updated = await client.patch(
                f"/customer-service/routing-policies/{body['id']}",
                json={
                    "strategy": "first_available",
                    "is_active": False,
                },
            )
            assert updated.status_code == 200
            assert updated.json()["strategy"] == "first_available"
            assert updated.json()["is_active"] is False

            active = await client.get(
                "/customer-service/routing-policies",
                params={"active_only": True},
            )
            assert active.status_code == 200
            assert all(item["id"] != body["id"] for item in active.json())

            deleted = await client.delete(
                f"/customer-service/routing-policies/{body['id']}"
            )
            assert deleted.status_code == 204

            missing = await client.get(
                f"/customer-service/routing-policies/{body['id']}"
            )
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_routing_policy_priority_and_fallback_fields():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        assignee = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/customer-service/routing-policies",
                json={
                    "name": "Fallback routing",
                    "strategy": "first_available",
                    "candidate_assignee_ids": [str(assignee)],
                    "priority_rank": 999,
                    "is_fallback": True,
                },
            )

            assert created.status_code == 200
            body = created.json()
            assert body["priority_rank"] == 999
            assert body["is_fallback"] is True

            updated = await client.patch(
                f"/customer-service/routing-policies/{body['id']}",
                json={
                    "priority_rank": 10,
                    "is_fallback": False,
                },
            )

            assert updated.status_code == 200
            assert updated.json()["priority_rank"] == 10
            assert updated.json()["is_fallback"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)
