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


def build_resolver():
    capabilities = CapabilityRegistry()
    capabilities.register_domain(CapabilityDomain(id="ecommerce", title="Ecommerce"))
    capabilities.register_category(
        CapabilityCategory(id="ecommerce.orders", domain_id="ecommerce", title="Orders")
    )
    capabilities.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.get",
            category_id="ecommerce.orders",
            title="Get Order",
            required_inputs=("order_ref",),
        )
    )

    providers = ProviderRegistry()
    providers.register(CapabilityProvider(id="shopify", title="Shopify", kind=CapabilityProviderKind.BUILTIN))
    providers.register(CapabilityProvider(id="mock", title="Mock", kind=CapabilityProviderKind.BUILTIN))

    bindings = BindingRegistry()
    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            required_inputs=("order_ref",),
            priority=100,
            enabled=False,
        )
    )
    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="mock",
            provider_ref="mock.get_order",
            required_inputs=("order_ref",),
            priority=10,
            enabled=True,
        )
    )

    return CapabilityResolver(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
    )


def test_disabled_preferred_provider_is_rejected_and_fallback_selected():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            preferred_provider_id="shopify",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "mock"
    assert result.provider_ref == "mock.get_order"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["shopify"] == "disabled"

    diagnostics = result.metadata["diagnostics"]
    assert diagnostics["selected_provider_id"] == "mock"
    assert any(
        item["provider_id"] == "shopify" and item["reason"] == "disabled"
        for item in diagnostics["rejected_providers"]
    )


def test_no_enabled_binding_returns_diagnostics():
    resolver = build_resolver()

    resolver.bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="mock",
            provider_ref="mock.get_order",
            required_inputs=("order_ref",),
            priority=10,
            enabled=False,
        )
    )

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert result.selected_provider_id is None
    assert result.metadata["diagnostics"]["status"] == "no_enabled_binding"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["shopify"] == "disabled"
    assert rejected["mock"] == "disabled"
