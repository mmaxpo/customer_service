from app.runtime.capabilities.registry.compatibility import (
    CapabilityAliasRegistry,
    build_default_capability_registry_v2,
)
from app.runtime.capabilities.registry.compatibility.aliases import (
    CapabilityAliasRegistry as CanonicalAliasRegistry,
)
from app.runtime.capabilities.registry.compatibility.v2_defaults import (
    build_default_capability_registry_v2 as CanonicalV2Builder,
)
from app.runtime.capabilities.registry.compatibility.v2_defaults import (
    build_default_capability_registry_v2 as LegacyDefaultsV2Builder,
)
from app.runtime.capabilities.registry.compatibility.aliases import (
    CapabilityAliasRegistry as LegacyAliasRegistry,
)


def test_alias_registry_old_path_is_compatibility_shim():
    assert CapabilityAliasRegistry is CanonicalAliasRegistry
    assert LegacyAliasRegistry is CanonicalAliasRegistry

    aliases = CapabilityAliasRegistry()
    aliases.register(
        "shopify.get_order",
        "ecommerce.orders.get",
    )

    assert (
        aliases.resolve("shopify.get_order")
        == "ecommerce.orders.get"
    )


def test_v2_defaults_old_path_is_compatibility_shim():
    assert build_default_capability_registry_v2 is CanonicalV2Builder
    assert LegacyDefaultsV2Builder is CanonicalV2Builder

    registry = build_default_capability_registry_v2()

    assert registry.has("shopify.get_order")
    assert registry.has("shopify.order_action")
