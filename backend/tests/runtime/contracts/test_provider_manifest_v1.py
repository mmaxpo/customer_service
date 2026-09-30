from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.compatibility.aliases import CapabilityAliasRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.providers.shopify.manifest import register_manifest
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def test_shopify_manifest_registers_complete_order_lookup_stack():
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry()
    bindings = BindingRegistry()
    aliases = CapabilityAliasRegistry()

    register_manifest(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )

    assert capabilities.has_capability("ecommerce.orders.get")
    assert providers.has("shopify")
    assert bindings.has("ecommerce.orders.get", "shopify")
    assert aliases.resolve("shopify.get_order") == "ecommerce.orders.get"


def test_shopify_manifest_resolves_legacy_order_lookup():
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry()
    bindings = BindingRegistry()
    aliases = CapabilityAliasRegistry()

    register_manifest(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )

    resolver = CapabilityResolver(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.get"
    assert result.selected_provider_id == "shopify"
    assert result.provider_ref == "shopify.get_order"
