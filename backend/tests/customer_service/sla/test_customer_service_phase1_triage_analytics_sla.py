from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "phase1-triage@example.com"
        self.customer_service_role = "owner"


@pytest.mark.asyncio
async def test_triage_applies_tags_priority_audit_and_workload_report():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Triage",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+491234",
                    },
                )
            ).json()
            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "email",
                        "subject": "Damaged item",
                    },
                )
            ).json()
            ticket = (await client.get("/customer-service/tickets/")).json()[0]

            triage = await client.post(
                f"/customer-service/conversations/{conversation['id']}/triage",
                json={"message": "Refund my damaged order urgently"},
            )
            assert triage.status_code == 200
            assert triage.json()["intent"] == "refund_request"
            assert "damaged_item" in triage.json()["tags"]

            updated = (
                await client.get(f"/customer-service/tickets/{ticket['id']}")
            ).json()
            assert updated["priority"] == "high"

            assignee = uuid4()
            await client.post(
                f"/customer-service/tickets/{ticket['id']}/assign",
                params={"assigned_to": str(assignee)},
            )
            workload = await client.get("/customer-service/analytics/workload")
            assert workload.status_code == 200
            assert workload.json()[0]["assigned_to"] == str(assignee)

            logs = await client.get(
                "/customer-service/audit-logs/",
                params={"entity_type": "conversation", "entity_id": conversation["id"]},
            )
            assert any(item["action"] == "conversation.triaged" for item in logs.json())
    finally:
        app.dependency_overrides.pop(get_current_user, None)
