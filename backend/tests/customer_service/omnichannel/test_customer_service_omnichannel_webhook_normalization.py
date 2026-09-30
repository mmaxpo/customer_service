import pytest

from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)
from app.domains.customer_service.schemas.omnichannel import (
    OmnichannelWebhookEventType,
)


@pytest.mark.asyncio
async def test_generic_provider_normalizes_webhook_payload():
    register_default_omnichannel_providers()

    registry = get_omnichannel_provider_registry()
    adapter = registry.get("whatsapp")

    event = await adapter.normalize_webhook_event(
        {
            "channel": "whatsapp",
            "external_account_id": "account-1",
            "external_thread_id": "thread-1",
            "external_message_id": "message-1",
            "external_customer_id": "customer-1",
            "customer_name": "Test Customer",
            "customer_email": "customer@example.com",
            "body": "Hello support",
        }
    )

    assert event.provider == "whatsapp"
    assert event.channel == "whatsapp"
    assert event.event_type == OmnichannelWebhookEventType.MESSAGE_INBOUND
    assert event.external_account_id == "account-1"
    assert event.external_message_id == "message-1"
    assert event.body == "Hello support"
