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
    CapabilityRisk,
    ProviderBinding,
)


def build():
    capabilities = CapabilityRegistry()
    capabilities.register_domain(CapabilityDomain(id="orders", title="Orders"))
    capabilities.register_category(CapabilityCategory(id="orders.actions", domain_id="orders", title="Actions"))
    capabilities.register_capability(CapabilityDefinition(id="orders.action", category_id="orders.actions", title="Order Action"))

    providers = ProviderRegistry()
    providers.register(CapabilityProvider(id="highrisk", title="High Risk", kind=CapabilityProviderKind.API))
    providers.register(CapabilityProvider(id="safe", title="Safe", kind=CapabilityProviderKind.API))

    bindings = BindingRegistry()
    bindings.register(ProviderBinding(capability_id="orders.action", provider_id="highrisk", provider_ref="highrisk.action", priority=100, risk=CapabilityRisk.HIGH))
    bindings.register(ProviderBinding(capability_id="orders.action", provider_id="safe", provider_ref="safe.action", priority=10, risk=CapabilityRisk.SAFE))

    return CapabilityResolver(capabilities=capabilities, providers=providers, bindings=bindings)


def test_risk_policy_rejects_high_risk_provider_and_selects_safe():
    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="orders.action",
            max_risk=CapabilityRisk.MEDIUM,
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "safe"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["highrisk"] == "risk_exceeds_limit"


def test_without_risk_policy_highest_priority_wins():
    result = build().resolve(CapabilityResolutionRequest(capability_id="orders.action"))

    assert result.ok is True
    assert result.selected_provider_id == "highrisk"
