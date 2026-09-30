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
    capabilities.register_domain(CapabilityDomain(id="ai", title="AI"))
    capabilities.register_category(CapabilityCategory(id="ai.llm", domain_id="ai", title="LLM"))
    capabilities.register_capability(CapabilityDefinition(id="ai.text.generate", category_id="ai.llm", title="Generate Text"))

    providers = ProviderRegistry()
    providers.register(CapabilityProvider(id="slow", title="Slow", kind=CapabilityProviderKind.API))
    providers.register(CapabilityProvider(id="fast", title="Fast", kind=CapabilityProviderKind.API))

    bindings = BindingRegistry()
    bindings.register(ProviderBinding(capability_id="ai.text.generate", provider_id="slow", provider_ref="slow.generate", priority=100, metadata={"latency_ms": 2000}))
    bindings.register(ProviderBinding(capability_id="ai.text.generate", provider_id="fast", provider_ref="fast.generate", priority=10, metadata={"latency_ms": 200}))

    return CapabilityResolver(capabilities=capabilities, providers=providers, bindings=bindings)


def test_latency_policy_rejects_slow_provider_and_selects_fast():
    result = build().resolve(CapabilityResolutionRequest(capability_id="ai.text.generate", max_latency_ms=500))

    assert result.ok is True
    assert result.selected_provider_id == "fast"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["slow"] == "latency_exceeds_limit"


def test_without_latency_policy_highest_priority_wins():
    result = build().resolve(CapabilityResolutionRequest(capability_id="ai.text.generate"))

    assert result.ok is True
    assert result.selected_provider_id == "slow"
