import pytest

from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)


@pytest.mark.asyncio
async def test_whatsapp_provider_normalizes_payload():
    register_default_omnichannel_providers()

    registry = get_omnichannel_provider_registry()
    adapter = registry.get("whatsapp")

    normalized = await adapter.normalize_inbound_message(
        {
            "external_account_id": "wa-business-1",
            "external_thread_id": "thread-1",
            "external_message_id": "message-1",
            "external_customer_id": "customer-1",
            "customer_phone": "+46700000000",
            "profile": {
                "name": "WhatsApp Customer",
            },
            "body": "Need help with my order",
        }
    )

    assert normalized.channel == "whatsapp"
    assert normalized.customer_name == "WhatsApp Customer"
    assert normalized.customer_phone == "+46700000000"
    assert normalized.body == "Need help with my order"
