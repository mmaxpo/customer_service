import pytest

from app.domains.customer_service.integrations.omnichannel.providers import (
    register_default_omnichannel_providers,
)
from app.domains.customer_service.integrations.omnichannel.registry import (
    get_omnichannel_provider_registry,
)


@pytest.mark.asyncio
async def test_generic_provider_webhook_verification():
    register_default_omnichannel_providers()

    registry = get_omnichannel_provider_registry()
    adapter = registry.get("whatsapp")

    result = await adapter.verify_webhook_signature(
        headers={
            "x-test-signature": "dummy",
        },
        body=b'{"message":"hello"}',
    )

    assert result.verified is True
    assert result.reason is None
