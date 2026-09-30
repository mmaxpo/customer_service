from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.state import ProviderAuthRegistry
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.state import TenantProviderRegistry
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def build():
    tenant = TenantProviderRegistry()
    tenant.enable(tenant_id="tenant", provider_id="shopify")
    tenant.enable(tenant_id="tenant", provider_id="mock")

    auth = ProviderAuthRegistry()

    resolver = CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
        aliases=build_default_capability_alias_registry_v3(),
        tenant_providers=tenant,
        provider_auth=auth,
    )

    return resolver, auth


def test_missing_auth_falls_back_to_mock():
    resolver, auth = build()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.selected_provider_id == "mock"

    rejected = {x.provider_id: x.reason for x in result.rejected_providers}
    assert rejected["shopify"] == "missing_auth"


def test_connected_provider_wins():
    resolver, auth = build()

    auth.connect(
        tenant_id="tenant",
        provider_id="shopify",
    )

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.selected_provider_id == "shopify"
