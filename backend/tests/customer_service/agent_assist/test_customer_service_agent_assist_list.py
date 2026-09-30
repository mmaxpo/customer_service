from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "agent-assist-list@example.com"


@pytest.mark.asyncio
async def test_list_conversation_agent_assist_suggestions():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "List Suggestions Customer",
                        "email": f"{uuid4()}@example.com",
                        "phone": "+49123456789",
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

            await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "My item arrived damaged and broken.",
                },
            )

            suggestion_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/agent-assist/reply-suggestion"
            )
            assert suggestion_res.status_code == 200
            suggestion = suggestion_res.json()

            list_res = await client.get(
                f"/customer-service/conversations/{conversation['id']}/agent-assist/suggestions"
            )
            assert list_res.status_code == 200

            suggestions = list_res.json()
            assert len(suggestions) >= 1
            assert suggestions[0]["id"] == suggestion["id"]
            assert suggestions[0]["conversation_id"] == conversation["id"]
            assert suggestions[0]["status"] == "generated"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
