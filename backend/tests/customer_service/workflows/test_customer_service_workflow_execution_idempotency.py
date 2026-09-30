from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()


@pytest.mark.asyncio
async def test_duplicate_inbound_message_does_not_create_duplicate_workflow_execution():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            seed = await client.post(
                "/customer-service/event-subscriptions/seed-shopify"
            )
            assert seed.status_code == 200

            external_message_id = f"msg-{uuid4()}"
            external_thread_id = f"thread-{uuid4()}"

            payload = {
                "channel": "chat",
                "external_account_id": "chat-idempotency",
                "external_thread_id": external_thread_id,
                "external_message_id": external_message_id,
                "external_customer_id": f"customer-{uuid4()}",
                "customer_name": "Idempotency Customer",
                "customer_email": f"{uuid4()}@example.com",
                "body": "I want a refund for order #1001",
            }

            first = await client.post(
                "/customer-service/omnichannel/inbound",
                json=payload,
            )
            assert first.status_code == 200
            assert first.json()["duplicate"] is False

            second = await client.post(
                "/customer-service/omnichannel/inbound",
                json=payload,
            )
            assert second.status_code == 200
            assert second.json()["duplicate"] is True

            executions = await client.get(
                f"/customer-service/conversations/{first.json()['conversation_id']}/workflow-executions"
            )
            assert executions.status_code == 200
            assert len(executions.json()) == 1

            jobs = await client.get("/jobs")
            assert jobs.status_code == 200

            matching_jobs = [
                job
                for job in jobs.json()
                if job["job_type"] == "workflow.run"
                and job["payload"]["extras"]["event"]["payload"]["external_message_id"]
                == external_message_id
            ]

            assert len(matching_jobs) == 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
