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
    capabilities.register_domain(CapabilityDomain(id="orders", title="Orders"))
    capabilities.register_category(CapabilityCategory(id="orders.actions", domain_id="orders", title="Actions"))
    capabilities.register_capability(CapabilityDefinition(id="orders.refund", category_id="orders.actions", title="Refund Order"))

    providers = ProviderRegistry()
    providers.register(CapabilityProvider(id="approval", title="Approval", kind=CapabilityProviderKind.API))
    providers.register(CapabilityProvider(id="safe", title="Safe", kind=CapabilityProviderKind.API))

    bindings = BindingRegistry()
    bindings.register(
        ProviderBinding(
            capability_id="orders.refund",
            provider_id="approval",
            provider_ref="approval.refund",
            priority=100,
            requires_approval=True,
        )
    )
    bindings.register(
        ProviderBinding(
            capability_id="orders.refund",
            provider_id="safe",
            provider_ref="safe.refund",
            priority=10,
            requires_approval=False,
        )
    )

    return CapabilityResolver(capabilities=capabilities, providers=providers, bindings=bindings)


def test_approval_policy_rejects_approval_required_provider_when_not_allowed():
    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="orders.refund",
            allow_approval_required=False,
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "safe"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["approval"] == "approval_required"


def test_approval_required_provider_can_win_when_allowed():
    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="orders.refund",
            allow_approval_required=True,
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "approval"
    assert result.requires_approval is True
