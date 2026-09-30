from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "sla@example.com"
        self.customer_service_role = "owner"


@pytest.mark.asyncio
async def test_sla_policy_and_targets_are_created_for_ticket():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            policy_res = await client.post(
                "/customer-service/sla/policies",
                json={
                    "name": "Normal SLA",
                    "priority": "normal",
                    "first_response_minutes": 60,
                    "resolution_minutes": 1440,
                    "is_active": True,
                },
            )
            assert policy_res.status_code == 200

            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "SLA Customer",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+49123456789",
                    },
                )
            ).json()

            conversation_res = await client.post(
                "/customer-service/conversations/",
                json={
                    "customer_id": customer["id"],
                    "channel": "email",
                    "subject": "SLA issue",
                },
            )
            assert conversation_res.status_code == 200

            violations_res = await client.get("/customer-service/sla/violations")
            assert violations_res.status_code == 200

            violations = violations_res.json()
            assert len(violations) == 2

            target_types = {v["target_type"] for v in violations}
            assert target_types == {"first_response", "resolution"}

            assert all(v["status"] == "open" for v in violations)

    finally:
        app.dependency_overrides.pop(get_current_user, None)
