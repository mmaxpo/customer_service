from app.runtime.capabilities.registry.registries import (
    BindingRegistry,
    CapabilityAliasRegistry,
    CapabilityRegistry,
    ProviderRegistry,
)


def test_registry_public_api_constructs_all_registries():
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry()
    bindings = BindingRegistry()
    aliases = CapabilityAliasRegistry()

    assert capabilities.capabilities == {}
    assert providers.providers == {}
    assert bindings.list() == []
    assert aliases.resolve("unknown.capability") == "unknown.capability"
