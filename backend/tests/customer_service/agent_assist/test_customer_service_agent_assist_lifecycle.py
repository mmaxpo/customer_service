from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "agent-assist-lifecycle@example.com"


@pytest.mark.asyncio
async def test_agent_assist_suggestion_lifecycle():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            customer = (
                await client.post(
                    "/customer-service/customers/",
                    json={
                        "name": "Lifecycle Customer",
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

            message_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/messages",
                json={
                    "sender_type": "customer",
                    "body": "My item arrived damaged and broken.",
                },
            )
            assert message_res.status_code == 200

            suggestion_res = await client.post(
                f"/customer-service/conversations/{conversation['id']}/agent-assist/reply-suggestion"
            )
            assert suggestion_res.status_code == 200
            suggestion = suggestion_res.json()

            assert suggestion["status"] == "generated"
            suggestion_id = suggestion["id"]

            revisions_res = await client.get(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/revisions"
            )
            assert revisions_res.status_code == 200
            revisions = revisions_res.json()
            assert len(revisions) == 1
            assert revisions[0]["revision_number"] == 1

            edit_res = await client.patch(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}",
                json={
                    "current_suggestion": "Sorry about that. Please send your order number and a photo.",
                    "change_reason": "make reply shorter",
                },
            )
            assert edit_res.status_code == 200
            edited = edit_res.json()
            assert edited["status"] == "edited"
            assert (
                edited["current_suggestion"]
                == "Sorry about that. Please send your order number and a photo."
            )

            revisions_res = await client.get(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/revisions"
            )
            assert revisions_res.status_code == 200
            revisions = revisions_res.json()
            assert len(revisions) == 2
            assert revisions[1]["revision_number"] == 2
            assert revisions[1]["change_reason"] == "make reply shorter"

            approve_res = await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/approve"
            )
            assert approve_res.status_code == 200
            assert approve_res.json()["status"] == "approved"

            send_res = await client.post(
                f"/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/send"
            )
            assert send_res.status_code == 200
            sent = send_res.json()
            assert sent["status"] == "sent"
            assert sent["sent_message_id"]

            detail_res = await client.get(
                f"/customer-service/conversations/{conversation['id']}"
            )
            assert detail_res.status_code == 200
            detail = detail_res.json()

            assert any(
                message["sender_type"] == "agent"
                and message["body"]
                == "Sorry about that. Please send your order number and a photo."
                for message in detail["messages"]
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
