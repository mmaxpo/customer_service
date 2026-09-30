import pytest

from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)


@pytest.mark.asyncio
async def test_instagram_provider_normalizes_payload():
    register_default_omnichannel_providers()

    adapter = get_omnichannel_provider_registry().get("instagram")

    normalized = await adapter.normalize_inbound_message(
        {
            "external_account_id": "ig-page-1",
            "external_thread_id": "ig-thread-1",
            "external_message_id": "ig-message-1",
            "external_customer_id": "ig-user-1",
            "sender": {
                "username": "shopper_123",
                "name": "Instagram Customer",
            },
            "body": "Do you ship to Sweden?",
        }
    )

    assert normalized.channel == "instagram"
    assert normalized.customer_name == "Instagram Customer"
    assert normalized.external_customer_id == "ig-user-1"
    assert normalized.body == "Do you ship to Sweden?"
