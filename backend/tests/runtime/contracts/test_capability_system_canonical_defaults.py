from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
    build_default_system,
)
from app.runtime.capabilities.registry.system import CapabilitySystem
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
)


def test_build_default_system_is_canonical_composition_root():
    system = build_default_system()

    assert isinstance(system, CapabilitySystem)

    assert system.capabilities.has_capability(
        "ecommerce.orders.get"
    )
    assert system.providers.has("shopify")
    assert not system.providers.has("mock")

    assert system.bindings.has(
        "ecommerce.orders.get",
        "shopify",
    )
    assert not system.bindings.has(
        "ecommerce.orders.get",
        "mock",
    )

    assert (
        system.aliases.resolve("shopify.get_order")
        == "ecommerce.orders.get"
    )


def test_canonical_system_can_include_mock_explicitly():
    system = build_default_system(
        include_mock_provider=True,
    )

    assert system.providers.has("shopify")
    assert system.providers.has("mock")
    assert system.bindings.has(
        "ecommerce.orders.get",
        "shopify",
    )
    assert system.bindings.has(
        "ecommerce.orders.get",
        "mock",
    )


def test_canonical_system_builds_working_resolver():
    system = build_default_system()

    result = system.build_resolver().resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.get"
    assert result.selected_provider_id == "shopify"


def test_versioned_v3_builders_remain_compatible_during_migration():
    capabilities = build_default_capability_registry_v3()
    providers = build_default_provider_registry_v3()
    bindings = build_default_binding_registry_v3()
    aliases = build_default_capability_alias_registry_v3()

    assert capabilities.has_capability("ecommerce.orders.get")
    assert providers.has("shopify")
    assert providers.has("mock")

    assert bindings.has(
        "ecommerce.orders.get",
        "shopify",
    )
    assert bindings.has(
        "ecommerce.orders.get",
        "mock",
    )

    assert (
        aliases.resolve("shopify.get_order")
        == "ecommerce.orders.get"
    )
