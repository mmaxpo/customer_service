from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.auth import get_current_user
from app.core.session import SessionLocal
from app.domains.customer_service.integrations.omnichannel.errors import (
    OmnichannelProviderTransientError,
)
from app.domains.customer_service.integrations.omnichannel.protocol import (
    NormalizedOutboundResult,
    OmnichannelDeliveryStatus,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.models import (
    CustomerServiceExternalMessageLink,
)
from app.main import app
from app.models.models import PlatformJob
from app.platform.jobs.worker import JobWorker


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-retry-success@example.com"


class RetryThenSuccessProvider:
    channel = "retry-success-test"

    def __init__(self):
        self.calls = 0

    def capabilities(self):
        return {
            "channel": self.channel,
            "supports_inbound": True,
            "supports_outbound": True,
            "supports_delivery_events": True,
            "supports_attachments": False,
            "supports_templates": False,
            "supports_read_receipts": False,
        }

    async def send_message(self, message):
        self.calls += 1

        if self.calls == 1:
            raise OmnichannelProviderTransientError(
                "temporary provider outage",
                code="temporary_outage",
            )

        return NormalizedOutboundResult(
            external_message_id=f"provider-msg-{message.idempotency_key}",
            delivery_status=OmnichannelDeliveryStatus.SENT,
            raw_response={
                "provider": self.channel,
                "calls": self.calls,
                "idempotency_key": message.idempotency_key,
            },
        )


@pytest.mark.asyncio
async def test_retry_then_success_creates_single_message_and_single_external_link(
    monkeypatch,
):
    user = FakeUser()
    provider = RetryThenSuccessProvider()

    registry = get_omnichannel_provider_registry()
    test_adapters = dict(registry._adapters)
    test_adapters[provider.channel] = provider
    monkeypatch.setattr(registry, "_adapters", test_adapters)

    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            inbound = await client.post(
                "/customer-service/omnichannel/inbound",
                json={
                    "channel": provider.channel,
                    "external_account_id": "acct-retry-success-1",
                    "external_thread_id": "thread-retry-success-1",
                    "external_message_id": "incoming-retry-success-1",
                    "external_customer_id": "customer-retry-success-1",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Hello",
                },
            )
            assert inbound.status_code == 200
            conversation_id = inbound.json()["conversation_id"]

            queued = await client.post(
                "/customer-service/omnichannel/outbound/enqueue",
                json={
                    "conversation_id": conversation_id,
                    "body": "Hello back",
                    "sender_type": "agent",
                    "idempotency_key": "retry-success-key",
                },
            )
            assert queued.status_code == 200
            job_id = queued.json()["job_id"]

        async with SessionLocal() as db:
            first = await JobWorker(
                db,
                worker_id="retry-success-worker-1",
            ).run_once(job_id=job_id)

            assert first.status == "queued"
            assert provider.calls == 1

            job = await db.get(PlatformJob, job_id)
            job.run_after = datetime.now(timezone.utc)
            await db.commit()

            second = await JobWorker(
                db,
                worker_id="retry-success-worker-2",
            ).run_once(job_id=job_id)

            assert second.status == "succeeded"
            assert provider.calls == 2
            assert (
                second.result["external_message_id"] == "provider-msg-retry-success-key"
            )

            result = await db.execute(
                select(CustomerServiceExternalMessageLink).where(
                    CustomerServiceExternalMessageLink.user_id == user.id,
                    CustomerServiceExternalMessageLink.conversation_id
                    == conversation_id,
                    CustomerServiceExternalMessageLink.direction == "outbound",
                )
            )
            outbound_links = list(result.scalars().all())

            assert len(outbound_links) == 1
            assert (
                outbound_links[0].external_message_id
                == "provider-msg-retry-success-key"
            )
            assert (
                outbound_links[0].meta["omnichannel"]["idempotency_key"]
                == "retry-success-key"
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
