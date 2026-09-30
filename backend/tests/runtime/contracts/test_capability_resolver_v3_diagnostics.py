from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def build_resolver():
    return CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
        aliases=build_default_capability_alias_registry_v3(),
    )


def test_diagnostics_for_successful_resolution():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    diagnostics = result.metadata["diagnostics"]

    assert diagnostics["requested_capability_id"] == "shopify.get_order"
    assert diagnostics["resolved_capability_id"] == "ecommerce.orders.get"
    assert diagnostics["selected_provider_id"] == "shopify"
    assert diagnostics["provider_ref"] == "shopify.get_order"
    assert diagnostics["runtime_node_type"] == "capability.invoke"
    assert diagnostics["missing_inputs"] == []
    assert diagnostics["status"] == "selected"


def test_diagnostics_for_missing_required_input():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={},
        )
    )

    diagnostics = result.metadata["diagnostics"]

    assert result.ok is False
    assert diagnostics["status"] == "missing_inputs"
    assert diagnostics["requested_capability_id"] == "shopify.get_order"
    assert diagnostics["resolved_capability_id"] == "ecommerce.orders.get"
    assert diagnostics["selected_provider_id"] == "shopify"
    assert diagnostics["missing_inputs"] == ["order_ref"]


def test_diagnostics_for_unknown_capability():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="unknown.capability",
            inputs={},
        )
    )

    diagnostics = result.metadata["diagnostics"]

    assert result.ok is False
    assert diagnostics["status"] == "capability_not_registered"
    assert diagnostics["requested_capability_id"] == "unknown.capability"
    assert diagnostics["resolved_capability_id"] == "unknown.capability"
    assert diagnostics["selected_provider_id"] is None
