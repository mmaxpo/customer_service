from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry,
    build_default_capability_alias_registry,
    build_default_capability_registry,
    build_default_manifest_loader,
    build_default_provider_registry,
    build_default_system,
)
from app.runtime.capabilities.registry.defaults.aliases import (
    build_default_capability_alias_registry as LegacyAliasBuilder,
)
from app.runtime.capabilities.registry.defaults.bindings import (
    build_default_binding_registry as LegacyBindingBuilder,
)
from app.runtime.capabilities.registry.defaults.capabilities import (
    build_default_capability_registry as LegacyCapabilityBuilder,
)
from app.runtime.capabilities.registry.defaults.loader import (
    build_default_manifest_loader as LegacyLoaderBuilder,
)
from app.runtime.capabilities.registry.defaults.providers import (
    build_default_provider_registry as LegacyProviderBuilder,
)
from app.runtime.capabilities.registry.defaults.system import (
    build_default_system as LegacySystemBuilder,
)


def test_builders_module_owns_component_default_builders():
    component_builders = (
        build_default_manifest_loader,
        build_default_capability_registry,
        build_default_provider_registry,
        build_default_binding_registry,
        build_default_capability_alias_registry,
    )

    assert all(
        builder.__module__.endswith(".defaults.builders")
        for builder in component_builders
    )


def test_system_module_owns_default_system_builder():
    assert build_default_system.__module__.endswith(
        ".capabilities.registry.system"
    )


def test_historical_default_modules_are_compatibility_shims():
    assert LegacyLoaderBuilder is build_default_manifest_loader
    assert LegacyCapabilityBuilder is build_default_capability_registry
    assert LegacyProviderBuilder is build_default_provider_registry
    assert LegacyBindingBuilder is build_default_binding_registry
    assert LegacyAliasBuilder is build_default_capability_alias_registry
    assert LegacySystemBuilder is build_default_system


def test_canonical_builders_preserve_expected_defaults():
    capabilities = build_default_capability_registry()
    providers = build_default_provider_registry()
    bindings = build_default_binding_registry()
    aliases = build_default_capability_alias_registry()
    system = build_default_system()

    assert capabilities.has_capability("ecommerce.orders.get")
    assert providers.has("shopify")
    assert providers.has("mock")
    assert bindings.has("ecommerce.orders.get", "shopify")
    assert bindings.has("ecommerce.orders.get", "mock")
    assert aliases.resolve("shopify.get_order") == "ecommerce.orders.get"
    assert system.capabilities.has_capability("ecommerce.orders.get")
