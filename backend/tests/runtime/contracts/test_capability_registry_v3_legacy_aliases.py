import pytest

from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.compatibility.aliases import CapabilityAliasRegistry
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def test_alias_registry_resolves_legacy_capability_id():
    aliases = CapabilityAliasRegistry()
    aliases.register("shopify.get_order", "ecommerce.orders.get")

    assert aliases.has("shopify.get_order")
    assert aliases.resolve("shopify.get_order") == "ecommerce.orders.get"
    assert aliases.resolve("ecommerce.orders.get") == "ecommerce.orders.get"


def test_alias_registry_is_deterministic():
    aliases = CapabilityAliasRegistry()
    aliases.register("z.old", "z.new")
    aliases.register("a.old", "a.new")

    assert aliases.list() == [
        ("a.old", "a.new"),
        ("z.old", "z.new"),
    ]


def test_alias_registry_rejects_empty_values():
    aliases = CapabilityAliasRegistry()

    with pytest.raises(ValueError):
        aliases.register("", "ecommerce.orders.get")

    with pytest.raises(ValueError):
        aliases.register("shopify.get_order", "")


def test_legacy_shopify_get_order_can_be_resolved_before_v3_resolver():
    aliases = CapabilityAliasRegistry()
    aliases.register("shopify.get_order", "ecommerce.orders.get")

    resolver = CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
    )

    semantic_id = aliases.resolve("shopify.get_order")

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id=semantic_id,
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.get"
    assert result.selected_provider_id == "shopify"
    assert result.provider_ref == "shopify.get_order"
