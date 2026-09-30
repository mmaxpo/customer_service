from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def test_default_v3_registries_include_shopify_order_lookup_mapping():
    capabilities = build_default_capability_registry_v3()
    providers = build_default_provider_registry_v3()
    bindings = build_default_binding_registry_v3()

    assert capabilities.has_capability("ecommerce.orders.get")
    assert providers.has("shopify")

    binding = bindings.get("ecommerce.orders.get", "shopify")
    assert binding.provider_ref == "shopify.get_order"
    assert binding.runtime_node_type == "capability.invoke"
    assert binding.required_inputs == ("order_ref",)


def test_default_v3_resolver_resolves_shopify_order_lookup():
    resolver = CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
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
    assert result.runtime_node_type == "capability.invoke"


def test_default_v3_resolver_reports_missing_order_ref():
    resolver = CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
    )

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.selected_provider_id == "shopify"
    assert result.missing_inputs == ("order_ref",)


def test_default_v3_shopify_order_action_binding_includes_scope():
    bindings = build_default_binding_registry_v3()

    binding = bindings.get(
        "ecommerce.orders.action",
        "shopify",
    )

    assert binding.provider_ref == "shopify.order_action"
    assert binding.runtime_node_type == "capability.invoke"
    assert "scope" in binding.optional_inputs
