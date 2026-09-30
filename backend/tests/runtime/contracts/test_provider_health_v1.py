from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.state import ProviderAuthRegistry
from app.runtime.capabilities.registry.state import ProviderHealthRegistry
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.state import TenantProviderRegistry
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def build():
    tenant = TenantProviderRegistry()
    tenant.enable(tenant_id="tenant", provider_id="shopify")
    tenant.enable(tenant_id="tenant", provider_id="mock")

    auth = ProviderAuthRegistry()
    auth.connect(tenant_id="tenant", provider_id="shopify")

    health = ProviderHealthRegistry()

    resolver = CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
        aliases=build_default_capability_alias_registry_v3(),
        tenant_providers=tenant,
        provider_auth=auth,
        provider_health=health,
    )

    return resolver, health


def test_unhealthy_shopify_falls_back_to_mock():
    resolver, health = build()

    health.mark_unhealthy("shopify")

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "mock"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["shopify"] == "provider_unhealthy"


def test_healthy_shopify_wins():
    resolver, health = build()

    health.mark_healthy("shopify")

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "shopify"


def test_provider_health_defaults_to_healthy():
    health = ProviderHealthRegistry()

    assert health.is_healthy("shopify") is True
