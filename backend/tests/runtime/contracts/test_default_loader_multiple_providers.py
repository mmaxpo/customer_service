from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def test_default_loader_registers_shopify_and_mock_providers():
    providers = build_default_provider_registry_v3()
    bindings = build_default_binding_registry_v3()

    assert providers.has("shopify")
    assert providers.has("mock")
    assert bindings.has("ecommerce.orders.get", "shopify")
    assert bindings.has("ecommerce.orders.get", "mock")


def test_default_resolver_selects_shopify_over_mock_by_priority():
    resolver = CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
        aliases=build_default_capability_alias_registry_v3(),
    )

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "shopify"
    assert result.provider_ref == "shopify.get_order"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["mock"] == "lower_priority"
