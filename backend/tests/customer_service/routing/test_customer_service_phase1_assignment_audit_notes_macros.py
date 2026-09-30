from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "phase1@example.com"
        self.customer_service_role = "owner"


async def _conversation(client):
    customer = (
        await client.post(
            "/customer-service/customers/",
            json={
                "name": "Phase 1",
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
                "subject": "Phase 1 ticket",
            },
        )
    ).json()
    ticket = (await client.get("/customer-service/tickets/")).json()[0]
    return conversation, ticket


@pytest.mark.asyncio
async def test_assignment_internal_note_macro_and_audit_log_flow():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            conversation, ticket = await _conversation(client)
            assignee = uuid4()
            assign = await client.post(
                f"/customer-service/tickets/{ticket['id']}/assign",
                params={"assigned_to": str(assignee)},
            )
            assert assign.status_code == 200

            note = await client.post(
                f"/customer-service/conversations/{conversation['id']}/internal-notes",
                json={"body": "Handle carefully"},
            )
            assert note.status_code == 200
            assert note.json()["sender_type"] == "internal_note"

            macro = await client.post(
                "/customer-service/macros/",
                json={"name": "Refund reply", "body": "We are checking your refund."},
            )
            assert macro.status_code == 200
            applied = await client.post(
                f"/customer-service/macros/{macro.json()['id']}/apply/{conversation['id']}"
            )
            assert applied.status_code == 200
            assert applied.json()["body"] == "We are checking your refund."

            logs = await client.get("/customer-service/audit-logs/")
            assert logs.status_code == 200
            actions = {item["action"] for item in logs.json()}
            assert "ticket.assigned" in actions
            assert "internal_note.created" in actions
            assert "macro.created" in actions
            assert "macro.applied" in actions
    finally:
        app.dependency_overrides.pop(get_current_user, None)
