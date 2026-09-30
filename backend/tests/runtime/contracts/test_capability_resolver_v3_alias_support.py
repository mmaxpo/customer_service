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


def test_resolver_accepts_legacy_shopify_get_order_id():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.get"
    assert result.metadata["requested_capability_id"] == "shopify.get_order"
    assert result.selected_provider_id == "shopify"
    assert result.provider_ref == "shopify.get_order"


def test_resolver_accepts_semantic_capability_id_without_alias_change():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.get"
    assert result.metadata["requested_capability_id"] == "ecommerce.orders.get"


def test_resolver_reports_missing_inputs_for_legacy_id_after_alias_resolution():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.capability_id == "ecommerce.orders.get"
    assert result.selected_provider_id == "shopify"
    assert result.missing_inputs == ("order_ref",)
    assert result.metadata["requested_capability_id"] == "shopify.get_order"
