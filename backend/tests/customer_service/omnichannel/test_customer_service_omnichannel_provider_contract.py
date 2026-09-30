import pytest

from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)


@pytest.mark.asyncio
async def test_registered_generic_provider_normalizes_inbound_message():
    register_default_omnichannel_providers()
    registry = get_omnichannel_provider_registry()
    adapter = registry.get("whatsapp")

    normalized = await adapter.normalize_inbound_message(
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

    assert normalized.channel == "whatsapp"
    assert normalized.external_account_id == "account-1"
    assert normalized.external_thread_id == "thread-1"
    assert normalized.external_message_id == "message-1"
    assert normalized.body == "Hello support"
