from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_conversation_workflow_execution_visible():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post("/customer-service/event-subscriptions/seed-shopify")

            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "chat",
                    "external_account_id": "chat-1",
                    "external_thread_id": f"thread-{uuid4()}",
                    "external_message_id": f"msg-{uuid4()}",
                    "external_customer_id": f"customer-{uuid4()}",
                    "customer_name": "Test User",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "I want a refund for order #1001",
                },
            )

            assert inbound.status_code == 200

            conversation_id = inbound.json()["conversation_id"]

            executions = await client.get(
                f"/customer-service/conversations/{conversation_id}/workflow-executions"
            )

            assert executions.status_code == 200

            rows = executions.json()

            assert len(rows) >= 1

            assert any(row["job_type"] == "workflow.run" for row in rows)

    finally:
        app.dependency_overrides.clear()
