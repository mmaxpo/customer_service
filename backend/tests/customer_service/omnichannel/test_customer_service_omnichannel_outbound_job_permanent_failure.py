from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderPermanentError,
)
from app.domains.customer_service.workflows.omnichannel_jobs import (
    OMNICHANNEL_OUTBOUND_SEND_JOB,
)
from app.platform.jobs.service import JobService
from app.platform.jobs.worker import JobWorker


@pytest.mark.asyncio
async def test_omnichannel_permanent_provider_error_dead_letters_immediately(
    monkeypatch,
):
    user_id = uuid4()
    conversation_id = uuid4()

    async def fail_send(*args, **kwargs):
        raise OmnichannelProviderPermanentError(
            "invalid recipient",
            code="invalid_recipient",
        )

    monkeypatch.setattr(
        "app.domains.customer_service.services.omnichannel.CustomerServiceOmnichannelService.send_outbound_message",
        fail_send,
    )

    async with SessionLocal() as db:
        job = await JobService(db).enqueue(
            job_type=OMNICHANNEL_OUTBOUND_SEND_JOB,
            user_id=user_id,
            max_attempts=3,
            payload={
                "user_id": str(user_id),
                "conversation_id": str(conversation_id),
                "channel": "whatsapp",
                "external_account_id": "wa-permanent-failure",
                "external_thread_id": "thread-permanent-failure",
                "body": "This should fail permanently",
                "sender_type": "agent",
                "idempotency_key": "permanent-failure-1",
                "meta": None,
            },
        )

        processed = await JobWorker(
            db,
            worker_id="test-permanent-failure-worker",
        ).run_once(job_id=job.id)

        assert processed.status == "dead_letter"
        assert processed.attempts == 1
        assert processed.max_attempts == 1
        assert "invalid recipient" in processed.error_message
