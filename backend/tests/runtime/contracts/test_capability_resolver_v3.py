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
    providers = ProviderRegistry()
    bindings = BindingRegistry()

    capabilities.register_domain(
        CapabilityDomain(id="ecommerce", title="Ecommerce")
    )
    capabilities.register_category(
        CapabilityCategory(
            id="ecommerce.orders",
            domain_id="ecommerce",
            title="Orders",
        )
    )
    capabilities.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.get",
            category_id="ecommerce.orders",
            title="Get Order",
            required_inputs=("order_ref",),
            output_key="shopify_order",
        )
    )

    providers.register(
        CapabilityProvider(
            id="shopify",
            title="Shopify",
            kind=CapabilityProviderKind.BUILTIN,
            requires_auth=True,
        )
    )

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            runtime_node_type="capability.invoke",
            required_inputs=("order_ref",),
            output_key="shopify_order",
            priority=100,
        )
    )

    return CapabilityResolver(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
    )


def test_resolver_selects_binding_for_capability():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "shopify"
    assert result.provider_ref == "shopify.get_order"
    assert result.runtime_node_type == "capability.invoke"
    assert result.missing_inputs == ()


def test_resolver_returns_missing_inputs():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.selected_provider_id == "shopify"
    assert result.missing_inputs == ("order_ref",)


def test_resolver_rejects_unknown_capability():
    resolver = build_resolver()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="unknown.capability",
        )
    )

    assert result.ok is False
    assert result.selected_provider_id is None
    assert "not registered" in result.explanation


def test_resolver_honors_preferred_provider_when_available():
    resolver = build_resolver()

    resolver.providers.register(
        CapabilityProvider(
            id="mock",
            title="Mock",
            kind=CapabilityProviderKind.BUILTIN,
        )
    )
    resolver.bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="mock",
            provider_ref="mock.get_order",
            runtime_node_type="capability.invoke",
            required_inputs=("order_ref",),
            priority=10,
        )
    )

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            preferred_provider_id="mock",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "mock"
    assert result.provider_ref == "mock.get_order"
