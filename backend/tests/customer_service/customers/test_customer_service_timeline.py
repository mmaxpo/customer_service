from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.main import app


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_conversation_timeline_types():

    user = FakeUser()

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Timeline User",
                        "email": "timeline@test.com",
                        "phone": "+49123456",
                    },
                )
            ).json()

            conversation = (
                await client.post(
                    "/customer-service/conversations/",
                    json={
                        "customer_id": customer["id"],
                        "channel": "chat",
                        "subject": "Timeline test",
                    },
                )
            ).json()

            cid = conversation["id"]

            for sender in [
                "customer",
                "agent",
                "ai",
                "internal_note",
                "system",
            ]:
                r = await client.post(
                    f"/customer-service/conversations/{cid}/messages",
                    json={"sender_type": sender, "body": f"{sender} message"},
                )

                assert r.status_code == 200

            detail = await client.get(f"/customer-service/conversations/{cid}")

            messages = detail.json()["messages"]

            assert len(messages) == 5

    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_timeline_includes_assignment_and_sla_events():
    from uuid import uuid4

    from httpx import ASGITransport, AsyncClient

    from app.api.auth import get_current_user
    from app.main import app

    class FakeUser:
        def __init__(self):
            self.id = uuid4()
            self.email = "timeline-assignment@example.com"
            self.customer_service_role = "owner"

    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/customer-service/sla/policies",
                json={
                    "name": "Normal SLA",
                    "priority": "normal",
                    "first_response_minutes": 60,
                    "resolution_minutes": 1440,
                    "is_active": True,
                },
            )

            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Timeline Assignment",
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
                        "subject": "Timeline assignment issue",
                    },
                )
            ).json()

            ticket = (await client.get("/customer-service/tickets/")).json()[0]

            assign = await client.post(
                f"/customer-service/tickets/{ticket['id']}/assign",
                params={"assigned_to": str(uuid4())},
            )
            assert assign.status_code == 200

            timeline = await client.get(
                f"/customer-service/conversations/{conversation['id']}/timeline"
            )

            assert timeline.status_code == 200

            types = {item["type"] for item in timeline.json()}

            assert "ticket_assigned" in types
            assert "sla_target" in types

    finally:
        app.dependency_overrides.pop(get_current_user, None)
