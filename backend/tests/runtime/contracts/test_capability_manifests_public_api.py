from app.runtime.capabilities.registry.manifests import (
    CapabilityManifestLoader,
)
from app.runtime.capabilities.registry.registries import (
    BindingRegistry,
    CapabilityAliasRegistry,
    CapabilityRegistry,
    ProviderRegistry,
)


def test_manifest_loader_runs_contributions_in_registration_order():
    calls: list[str] = []

    def first(**kwargs) -> None:
        calls.append("first")

    def second(**kwargs) -> None:
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
