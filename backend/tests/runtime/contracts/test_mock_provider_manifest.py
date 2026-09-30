from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.compatibility.aliases import CapabilityAliasRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.providers.shopify.manifest import register_manifest as register_shopify
from app.runtime.capabilities.registry.providers.mock.manifest import register_manifest as register_mock


def test_mock_manifest_registers_provider_and_binding():
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry()
    bindings = BindingRegistry()
    aliases = CapabilityAliasRegistry()

    register_shopify(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )

    register_mock(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )

    assert providers.has("shopify")
    assert providers.has("mock")

    shopify = bindings.get("ecommerce.orders.get", "shopify")
    mock = bindings.get("ecommerce.orders.get", "mock")

    assert shopify.priority > mock.priority
    assert shopify.provider_ref == "shopify.get_order"
    assert mock.provider_ref == "mock.get_order"
