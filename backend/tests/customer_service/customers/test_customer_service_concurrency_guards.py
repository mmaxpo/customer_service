from uuid import uuid4

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    id = uuid4()
    email = "concurrency-guards@example.com"


@pytest.mark.asyncio
async def test_concurrent_duplicate_inbound_message_is_idempotent():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    external_message_id = f"msg-{uuid4()}"
    external_thread_id = f"thread-{uuid4()}"

    payload = {
        "provider": "generic",
        "external_account_id": "concurrency-guard",
        "external_thread_id": external_thread_id,
        "external_message_id": external_message_id,
        "channel": "chat",
        "customer_name": "Concurrent Customer",
        "customer_email": f"{uuid4()}@example.com",
        "body": "I need a refund",
        "direction": "inbound",
        "metadata": {
            "classification": {"intent": "refund_request"},
            "action": {"ticket_priority": "normal"},
        },
    }

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first, second = await asyncio.gather(
                client.post("/customer-service/omnichannel/inbound", json=payload),
                client.post("/customer-service/omnichannel/inbound", json=payload),
            )

            assert first.status_code == 200, first.text
            assert second.status_code == 200, second.text

            bodies = [first.json(), second.json()]
            assert sorted(item["duplicate"] for item in bodies) == [False, True]

            conversation_ids = {item["conversation_id"] for item in bodies}
            ticket_ids = {item["ticket_id"] for item in bodies}

            assert len(conversation_ids) == 1
            assert len(ticket_ids) == 1
    finally:
        app.dependency_overrides.clear()
