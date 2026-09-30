from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.main import app


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.customer_service_role = "owner"
        self.email = "agents@example.com"


@pytest.mark.asyncio
async def test_create_list_update_delete_customer_service_agent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        agent_user_id = uuid4()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/customer-service/agents",
                json={
                    "agent_user_id": str(agent_user_id),
                    "display_name": "Sarah Support",
                    "email": "sarah@example.com",
                    "skills": ["refunds", "shipping"],
                    "channels": ["whatsapp", "email"],
                    "languages": ["en", "fa"],
                    "max_open_tickets": 10,
                },
            )

            assert created.status_code == 200
            body = created.json()
            assert body["display_name"] == "Sarah Support"
            assert body["agent_user_id"] == str(agent_user_id)
            assert "refunds" in body["skills"]

            listed = await client.get("/customer-service/agents")
            assert listed.status_code == 200
            assert any(item["id"] == body["id"] for item in listed.json())

            available = await client.get(
                "/customer-service/agents",
                params={"active_only": True, "available_only": True},
            )
            assert available.status_code == 200
            assert any(item["id"] == body["id"] for item in available.json())

            updated = await client.patch(
                f"/customer-service/agents/{body['id']}",
                json={
                    "availability": "away",
                    "skills": ["refunds"],
                    "max_open_tickets": 5,
                },
            )
            assert updated.status_code == 200
            assert updated.json()["availability"] == "away"
            assert updated.json()["max_open_tickets"] == 5

            deleted = await client.delete(f"/customer-service/agents/{body['id']}")
            assert deleted.status_code == 204

            missing = await client.get(f"/customer-service/agents/{body['id']}")
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
