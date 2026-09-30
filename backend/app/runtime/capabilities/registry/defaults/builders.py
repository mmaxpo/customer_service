from __future__ import annotations

from app.runtime.capabilities.registry.manifests import (
    CapabilityManifestLoader,
)
from app.runtime.capabilities.registry.providers.mock.manifest import (
    register_manifest as register_mock_manifest,
)
from app.runtime.capabilities.registry.providers.shopify.manifest import (
    register_manifest as register_shopify_manifest,
)
from app.runtime.capabilities.registry.registries import (
    BindingRegistry,
    CapabilityAliasRegistry,
    CapabilityRegistry,
    ProviderRegistry,
)
from app.runtime.capabilities.registry.state import (
    ProviderAuthRegistry,
    ProviderHealthRegistry,
    TenantProviderRegistry,
)
from app.runtime.capabilities.registry.system import (
    CapabilitySystem,
    build_default_system,
)


def build_default_manifest_loader(
    *,
    include_mock_provider: bool = True,
) -> CapabilityManifestLoader:
    """
    Build the compatibility manifest loader.

    The compatibility registry builders retain mock-provider inclusion by
    default because existing resolver tests use them to exercise selection.
    Production RuntimeServiceFactory composition uses build_default_system(),
    whose default excludes test providers.
    """

    loader = CapabilityManifestLoader()
    loader.register_manifest(register_shopify_manifest)

    if include_mock_provider:
        loader.register_manifest(register_mock_manifest)

    return loader


def _load_default_components(
    *,
    capabilities: CapabilityRegistry,
    providers: ProviderRegistry,
    bindings: BindingRegistry,
    aliases: CapabilityAliasRegistry,
) -> None:
    build_default_manifest_loader().load(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )


def build_default_capability_registry() -> CapabilityRegistry:
    capabilities = CapabilityRegistry()

    _load_default_components(
        capabilities=capabilities,
        providers=ProviderRegistry(),
        bindings=BindingRegistry(),
        aliases=CapabilityAliasRegistry(),
    )

    return capabilities


def build_default_provider_registry() -> ProviderRegistry:
    providers = ProviderRegistry()

    _load_default_components(
        capabilities=CapabilityRegistry(),
        providers=providers,
        bindings=BindingRegistry(),
        aliases=CapabilityAliasRegistry(),
    )

    return providers


def build_default_binding_registry() -> BindingRegistry:
    bindings = BindingRegistry()

    _load_default_components(
        capabilities=CapabilityRegistry(),
        providers=ProviderRegistry(),
        bindings=bindings,
        aliases=CapabilityAliasRegistry(),
    )

    return bindings


def build_default_capability_alias_registry() -> CapabilityAliasRegistry:
    aliases = CapabilityAliasRegistry()

    _load_default_components(
        capabilities=CapabilityRegistry(),
        providers=ProviderRegistry(),
        bindings=BindingRegistry(),
        aliases=aliases,
    )

    return aliases


# Temporary V3 compatibility aliases.
build_default_manifest_loader_v3 = build_default_manifest_loader
build_default_capability_registry_v3 = build_default_capability_registry
build_default_provider_registry_v3 = build_default_provider_registry
build_default_binding_registry_v3 = build_default_binding_registry
build_default_capability_alias_registry_v3 = (
    build_default_capability_alias_registry
)


__all__ = [
    "build_default_manifest_loader",
    "build_default_capability_registry",
    "build_default_provider_registry",
    "build_default_binding_registry",
    "build_default_capability_alias_registry",
    "build_default_system",
    "build_default_manifest_loader_v3",
    "build_default_capability_registry_v3",
    "build_default_provider_registry_v3",
    "build_default_binding_registry_v3",
    "build_default_capability_alias_registry_v3",
]
