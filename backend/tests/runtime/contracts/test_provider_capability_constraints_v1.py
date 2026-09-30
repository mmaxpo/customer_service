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

    capabilities.register_domain(
        CapabilityDomain(
            id="orders",
            title="Orders",
        )
    )

    capabilities.register_category(
        CapabilityCategory(
            id="orders.actions",
            domain_id="orders",
            title="Actions",
        )
    )

    capabilities.register_capability(
        CapabilityDefinition(
            id="orders.operation",
            category_id="orders.actions",
            title="Order Operation",
        )
    )

    providers = ProviderRegistry()

    providers.register(
        CapabilityProvider(
            id="lookup_only",
            title="Lookup",
            kind=CapabilityProviderKind.API,
        )
    )

    providers.register(
        CapabilityProvider(
            id="full_provider",
            title="Full",
            kind=CapabilityProviderKind.API,
        )
    )

    bindings = BindingRegistry()

    bindings.register(
        ProviderBinding(
            capability_id="orders.operation",
            provider_id="lookup_only",
            provider_ref="lookup.operation",
            priority=100,
            metadata={
                "supported_actions": (
                    "lookup",
                ),
            },
        )
    )

    bindings.register(
        ProviderBinding(
            capability_id="orders.operation",
            provider_id="full_provider",
            provider_ref="full.operation",
            priority=10,
            metadata={
                "supported_actions": (
                    "lookup",
                    "refund",
                    "cancel",
                ),
            },
        )
    )

    return CapabilityResolver(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
    )


def test_required_action_selects_matching_provider():

    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="orders.operation",
            required_action="refund",
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "full_provider"

    rejected = {
        x.provider_id: x.reason
        for x in result.rejected_providers
    }

    assert rejected["lookup_only"] == "action_not_supported"


def test_without_required_action_highest_priority_wins():

    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="orders.operation",
        )
    )

    assert result.ok
    assert result.selected_provider_id == "lookup_only"
