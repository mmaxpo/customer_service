from app.runtime.capabilities.registry import (
    BindingRegistry,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityRegistry,
    CapabilityResolver,
    CapabilitySystem,
    ProviderRegistry,
    build_default_system,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory as CanonicalCapabilityCategory,
    CapabilityDefinition as CanonicalCapabilityDefinition,
)


def test_package_root_unversioned_names_are_current_contracts():
    assert CapabilityDefinition is CanonicalCapabilityDefinition
    assert CapabilityCategory is CanonicalCapabilityCategory


def test_package_root_exports_current_system_and_registries():
    system = build_default_system()

    assert isinstance(system, CapabilitySystem)
    assert isinstance(system.capabilities, CapabilityRegistry)
    assert isinstance(system.providers, ProviderRegistry)
    assert isinstance(system.bindings, BindingRegistry)
    assert isinstance(system.build_resolver(), CapabilityResolver)
