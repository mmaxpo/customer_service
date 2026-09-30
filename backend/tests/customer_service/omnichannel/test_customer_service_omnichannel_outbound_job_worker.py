from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.main import app
from app.platform.jobs.worker import JobWorker


class FakeUser:
    id = uuid4()


@pytest.mark.asyncio
async def test_omnichannel_outbound_delivery_job_worker_sends_message():
    user = FakeUser()
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": "whatsapp",
                    "external_account_id": "wa-business-worker-1",
                    "external_thread_id": "thread-worker-1",
                    "external_message_id": "message-inbound-worker-1",
                    "external_customer_id": "customer-worker-1",
                    "customer_name": "Worker Customer",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Hello",
                },
            )
            assert inbound.status_code == 200

            queued = await client.post(
                "/customer-service/omnichannel/outbound/enqueue",
                json={
                    "conversation_id": inbound.json()["conversation_id"],
                    "body": "Worker sent reply",
                    "sender_type": "agent",
                    "idempotency_key": "worker-outbound-1",
                },
            )
            assert queued.status_code == 200
            job_id = queued.json()["job_id"]

        async with SessionLocal() as db:
            processed = await JobWorker(
                db,
                worker_id="test-cs-omnichannel-worker",
            ).run_once(job_id=job_id)

            assert processed is not None
            assert processed.status == "succeeded"
            assert processed.result["external_message_id"] == "worker-outbound-1"
            await db.commit()
    finally:
        app.dependency_overrides.clear()
