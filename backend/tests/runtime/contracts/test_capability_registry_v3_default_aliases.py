from app.runtime.capabilities.registry.defaults import (
    build_default_capability_alias_registry_v3,
)


def test_default_alias_registry_maps_shopify_get_order_to_semantic_capability():
    aliases = build_default_capability_alias_registry_v3()

    assert aliases.resolve("shopify.get_order") == "ecommerce.orders.get"
    assert aliases.resolve("ecommerce.orders.get") == "ecommerce.orders.get"
