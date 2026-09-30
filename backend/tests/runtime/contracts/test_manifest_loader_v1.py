from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.compatibility.aliases import CapabilityAliasRegistry
from app.runtime.capabilities.registry.manifests import CapabilityManifestLoader
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.providers.shopify.manifest import register_manifest


def test_manifest_loader_loads_shopify_manifest():
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry()
    bindings = BindingRegistry()
    aliases = CapabilityAliasRegistry()

    loader = CapabilityManifestLoader()
    loader.register_manifest(register_manifest)

    loader.load(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )

    assert capabilities.has_capability("ecommerce.orders.get")
    assert providers.has("shopify")
    assert bindings.has("ecommerce.orders.get", "shopify")
    assert aliases.resolve("shopify.get_order") == "ecommerce.orders.get"


def test_manifest_loader_can_load_multiple_manifests_deterministically():
    calls = []

    def first(**kwargs):
        calls.append("first")

    def second(**kwargs):
        calls.append("second")

    loader = CapabilityManifestLoader()
    loader.register_manifest(first)
    loader.register_manifest(second)

    loader.load(
        capabilities=CapabilityRegistry(),
        providers=ProviderRegistry(),
        bindings=BindingRegistry(),
        aliases=CapabilityAliasRegistry(),
    )

    assert calls == ["first", "second"]
