import pytest

from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.state import TenantProviderRegistry
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def build_resolver(tenant_providers: TenantProviderRegistry):
    return CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
        aliases=build_default_capability_alias_registry_v3(),
        tenant_providers=tenant_providers,
    )


def test_tenant_provider_registry_register_enable_disable():
    registry = TenantProviderRegistry()

    registry.register_provider(
        tenant_id="tenant_1",
        provider_id="shopify",
        enabled=True,
    )

    assert registry.is_enabled(tenant_id="tenant_1", provider_id="shopify") is True

    registry.disable(tenant_id="tenant_1", provider_id="shopify")
    assert registry.is_enabled(tenant_id="tenant_1", provider_id="shopify") is False

    registry.enable(tenant_id="tenant_1", provider_id="shopify")
    assert registry.list_enabled(tenant_id="tenant_1") == ["shopify"]


def test_tenant_provider_registry_rejects_empty_values():
    registry = TenantProviderRegistry()

    with pytest.raises(ValueError):
        registry.register_provider(tenant_id="", provider_id="shopify")

    with pytest.raises(ValueError):
        registry.register_provider(tenant_id="tenant_1", provider_id="")


def test_resolver_selects_shopify_when_enabled_for_tenant():
    tenant_providers = TenantProviderRegistry()
    tenant_providers.enable(tenant_id="tenant_1", provider_id="shopify")
    tenant_providers.enable(tenant_id="tenant_1", provider_id="mock")

    resolver = build_resolver(tenant_providers)

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant_1",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "shopify"


def test_resolver_falls_back_to_mock_when_shopify_disabled_for_tenant():
    tenant_providers = TenantProviderRegistry()
    tenant_providers.disable(tenant_id="tenant_1", provider_id="shopify")
    tenant_providers.enable(tenant_id="tenant_1", provider_id="mock")

    resolver = build_resolver(tenant_providers)

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant_1",
            preferred_provider_id="shopify",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "mock"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["shopify"] == "disabled_for_tenant"


def test_resolver_returns_no_enabled_binding_when_all_disabled_for_tenant():
    tenant_providers = TenantProviderRegistry()
    tenant_providers.disable(tenant_id="tenant_1", provider_id="shopify")
    tenant_providers.disable(tenant_id="tenant_1", provider_id="mock")

    resolver = build_resolver(tenant_providers)

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            tenant_id="tenant_1",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert result.selected_provider_id is None
    assert result.metadata["diagnostics"]["status"] == "no_enabled_binding"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["shopify"] == "disabled_for_tenant"
    assert rejected["mock"] == "disabled_for_tenant"
