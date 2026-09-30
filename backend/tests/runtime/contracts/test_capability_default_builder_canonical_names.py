from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry,
    build_default_binding_registry_v3,
    build_default_capability_alias_registry,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry,
    build_default_capability_registry_v3,
    build_default_manifest_loader,
    build_default_manifest_loader_v3,
    build_default_provider_registry,
    build_default_provider_registry_v3,
)


def test_unversioned_default_builders_are_canonical():
    assert (
        build_default_manifest_loader_v3
        is build_default_manifest_loader
    )
    assert (
        build_default_capability_registry_v3
        is build_default_capability_registry
    )
    assert (
        build_default_provider_registry_v3
        is build_default_provider_registry
    )
    assert (
        build_default_binding_registry_v3
        is build_default_binding_registry
    )
    assert (
        build_default_capability_alias_registry_v3
        is build_default_capability_alias_registry
    )


def test_unversioned_default_builders_load_expected_contributions():
    capabilities = build_default_capability_registry()
    providers = build_default_provider_registry()
    bindings = build_default_binding_registry()
    aliases = build_default_capability_alias_registry()

    assert capabilities.has_capability("ecommerce.orders.get")
    assert providers.has("shopify")
    assert providers.has("mock")
    assert bindings.has("ecommerce.orders.get", "shopify")
    assert bindings.has("ecommerce.orders.get", "mock")
    assert aliases.resolve("shopify.get_order") == "ecommerce.orders.get"
