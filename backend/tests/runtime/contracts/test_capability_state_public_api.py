from app.runtime.capabilities.registry.state import (
    ProviderAuthRegistry,
    ProviderHealthRegistry,
    TenantProviderRegistry,
)


def test_state_public_api_supports_provider_lifecycle():
    tenant_providers = TenantProviderRegistry()
    provider_auth = ProviderAuthRegistry()
    provider_health = ProviderHealthRegistry()

    tenant_providers.enable(
        tenant_id="tenant_1",
        provider_id="shopify",
    )
    provider_auth.connect(
        tenant_id="tenant_1",
        provider_id="shopify",
    )
    provider_health.mark_healthy("shopify")

    assert tenant_providers.is_enabled(
        tenant_id="tenant_1",
        provider_id="shopify",
    )
    assert provider_auth.has_auth(
        tenant_id="tenant_1",
        provider_id="shopify",
    )
    assert provider_health.is_healthy("shopify")
