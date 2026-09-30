from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.domains.customer_service.integrations.omnichannel.protocol import (
    NormalizedOutboundResult,
    OmnichannelDeliveryStatus,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.main import app
from app.api.auth import get_current_user


class FakeUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "omnichannel-provider-call-idempotency@example.com"


class CountingSuccessProvider:
    channel = "counting-success-provider"

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
        return NormalizedOutboundResult(
            external_message_id=f"provider-message-{message.idempotency_key}",
            delivery_status=OmnichannelDeliveryStatus.SENT,
            raw_response={
                "calls": self.calls,
                "idempotency_key": message.idempotency_key,
            },
        )


@pytest.mark.asyncio
async def test_same_outbound_idempotency_key_after_provider_success_does_not_call_provider_twice(
    monkeypatch,
):
    """
    Production harsh case:

    Provider send succeeds, then the same outbound request/job is retried.

    Expected:
      - first request calls provider
      - second request returns existing message/link
      - provider is NOT called again
    """
    user = FakeUser()
    provider = CountingSuccessProvider()

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
                    "external_account_id": "provider-call-acct-1",
                    "external_thread_id": "provider-call-thread-1",
                    "external_message_id": "provider-call-inbound-1",
                    "external_customer_id": "provider-call-customer-1",
                    "customer_email": f"{uuid4()}@example.com",
                    "body": "Hello",
                },
            )

            assert inbound.status_code == 200
            conversation_id = inbound.json()["conversation_id"]

            payload = {
                "conversation_id": conversation_id,
                "body": "Hello back",
                "sender_type": "agent",
                "idempotency_key": "provider-call-idempotency-key-1",
            }

            first = await client.post(
                "/customer-service/omnichannel/outbound",
                json=payload,
            )
            second = await client.post(
                "/customer-service/omnichannel/outbound",
                json=payload,
            )

            assert first.status_code == 200
            assert second.status_code == 200

            assert provider.calls == 1

            first_data = first.json()
            second_data = second.json()

            assert second_data["message_id"] == first_data["message_id"]
            assert (
                second_data["external_message_id"] == first_data["external_message_id"]
            )
            assert (
                first_data["external_message_id"]
                == "provider-message-provider-call-idempotency-key-1"
            )

    finally:
        app.dependency_overrides.pop(get_current_user, None)
