from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)


def test_whatsapp_provider_capabilities():
    register_default_omnichannel_providers()

    adapter = get_omnichannel_provider_registry().get("whatsapp")
    capabilities = adapter.capabilities()

    assert capabilities.channel == "whatsapp"
    assert capabilities.supports_inbound is True
    assert capabilities.supports_outbound is True
    assert capabilities.supports_read_receipts is True
    assert capabilities.supports_attachments is True
    assert capabilities.supports_templates is True


def test_instagram_provider_capabilities():
    register_default_omnichannel_providers()

    adapter = get_omnichannel_provider_registry().get("instagram")
    capabilities = adapter.capabilities()

    assert capabilities.channel == "instagram"
    assert capabilities.supports_inbound is True
    assert capabilities.supports_outbound is True
    assert capabilities.supports_read_receipts is True
    assert capabilities.supports_attachments is True
    assert capabilities.supports_templates is False
