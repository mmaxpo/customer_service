from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import (
    CapabilityDefinition,
    CapabilityProvider,
    CapabilityProviderKind,
    CapabilityResolutionRequest,
    ProviderBinding,
)


def build():

    capabilities = CapabilityRegistry()

    from app.runtime.capabilities.registry.contracts import CapabilityDomain, CapabilityCategory

    capabilities.register_domain(
        CapabilityDomain(id="ecommerce", title="Ecommerce")
    )
    capabilities.register_category(
        CapabilityCategory(
            id="orders",
            domain_id="ecommerce",
            title="Orders",
        )
    )
    capabilities.register_capability(
        CapabilityDefinition(
            id="ecommerce.orders.get",
            category_id="orders",
            title="Get",
        )
    )

    providers = ProviderRegistry()

    providers.register(
        CapabilityProvider(
            id="shopify",
            title="Shopify",
            kind=CapabilityProviderKind.BUILTIN,
        )
    )

    providers.register(
        CapabilityProvider(
            id="mock",
            title="Mock",
            kind=CapabilityProviderKind.BUILTIN,
        )
    )

    bindings = BindingRegistry()

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            priority=100,
        )
    )

    bindings.register(
        ProviderBinding(
            capability_id="ecommerce.orders.get",
            provider_id="mock",
            provider_ref="mock.get_order",
            priority=10,
        )
    )

    return CapabilityResolver(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
    )


def test_highest_priority_selected():

    resolver = build()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
        )
    )

    assert result.ok
    assert result.selected_provider_id == "shopify"


def test_preferred_provider_wins():

    resolver = build()

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            preferred_provider_id="mock",
        )
    )

    assert result.selected_provider_id == "mock"
