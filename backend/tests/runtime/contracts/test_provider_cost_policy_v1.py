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
    capabilities.register_category(
        CapabilityCategory(id="ai.llm", domain_id="ai", title="LLM")
    )
    capabilities.register_capability(
        CapabilityDefinition(
            id="ai.text.generate",
            category_id="ai.llm",
            title="Generate Text",
        )
    )

    providers = ProviderRegistry()
    providers.register(CapabilityProvider(id="expensive", title="Expensive", kind=CapabilityProviderKind.API))
    providers.register(CapabilityProvider(id="cheap", title="Cheap", kind=CapabilityProviderKind.API))

    bindings = BindingRegistry()
    bindings.register(
        ProviderBinding(
            capability_id="ai.text.generate",
            provider_id="expensive",
            provider_ref="expensive.generate",
            priority=100,
            metadata={"cost": 10.0},
        )
    )
    bindings.register(
        ProviderBinding(
            capability_id="ai.text.generate",
            provider_id="cheap",
            provider_ref="cheap.generate",
            priority=10,
            metadata={"cost": 1.0},
        )
    )

    return CapabilityResolver(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
    )


def test_cost_policy_rejects_expensive_provider_and_selects_cheap():
    resolver = build()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ai.text.generate",
            max_cost=2.0,
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "cheap"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["expensive"] == "cost_exceeds_limit"


def test_without_cost_policy_highest_priority_wins():
    resolver = build()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ai.text.generate",
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "expensive"
