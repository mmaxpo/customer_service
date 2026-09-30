from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityDomain,
    CapabilityProvider,
    CapabilityProviderKind,
    CapabilityResolutionRequest,
    ProviderBinding,
)


def build():
    capabilities = CapabilityRegistry()
    capabilities.register_domain(CapabilityDomain(id="data", title="Data"))
    capabilities.register_category(CapabilityCategory(id="data.storage", domain_id="data", title="Storage"))
    capabilities.register_capability(CapabilityDefinition(id="data.store", category_id="data.storage", title="Store Data"))

    providers = ProviderRegistry()
    providers.register(CapabilityProvider(id="us_provider", title="US", kind=CapabilityProviderKind.API))
    providers.register(CapabilityProvider(id="eu_provider", title="EU", kind=CapabilityProviderKind.API))

    bindings = BindingRegistry()
    bindings.register(ProviderBinding(capability_id="data.store", provider_id="us_provider", provider_ref="us.store", priority=100, metadata={"regions": ("us",)}))
    bindings.register(ProviderBinding(capability_id="data.store", provider_id="eu_provider", provider_ref="eu.store", priority=10, metadata={"regions": ("eu",)}))

    return CapabilityResolver(capabilities=capabilities, providers=providers, bindings=bindings)


def test_region_policy_rejects_unsupported_region_and_selects_eu():
    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="data.store",
            required_region="eu",
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "eu_provider"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["us_provider"] == "region_not_supported"


def test_without_region_policy_highest_priority_wins():
    result = build().resolve(CapabilityResolutionRequest(capability_id="data.store"))

    assert result.ok is True
    assert result.selected_provider_id == "us_provider"
