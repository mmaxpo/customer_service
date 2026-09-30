from __future__ import annotations

from dataclasses import dataclass

from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
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
    CapabilityAliasRegistry,
)
from app.runtime.capabilities.registry.state import (
    ProviderAuthRegistry,
)
from app.runtime.capabilities.registry.state import (
    ProviderHealthRegistry,
)
from app.runtime.capabilities.registry.registries import (
    ProviderRegistry,
)
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.state import (
    TenantProviderRegistry,
)


@dataclass
class CapabilitySystem:
    capabilities: CapabilityRegistry
    providers: ProviderRegistry
    bindings: BindingRegistry
    aliases: CapabilityAliasRegistry

    tenant_providers: TenantProviderRegistry | None = None
    provider_auth: ProviderAuthRegistry | None = None
    provider_health: ProviderHealthRegistry | None = None

    def build_resolver(self) -> CapabilityResolver:
        return CapabilityResolver(
            capabilities=self.capabilities,
            providers=self.providers,
            bindings=self.bindings,
            aliases=self.aliases,
            tenant_providers=self.tenant_providers,
            provider_auth=self.provider_auth,
            provider_health=self.provider_health,
        )


def build_default_system(
    *,
    tenant_providers: TenantProviderRegistry | None = None,
    provider_auth: ProviderAuthRegistry | None = None,
    provider_health: ProviderHealthRegistry | None = None,
    include_mock_provider: bool = False,
) -> CapabilitySystem:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry()
    bindings = BindingRegistry()
    aliases = CapabilityAliasRegistry()

    loader = CapabilityManifestLoader()
    loader.register_manifest(register_shopify_manifest)

    if include_mock_provider:
        loader.register_manifest(register_mock_manifest)

    loader.load(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
    )

    return CapabilitySystem(
        capabilities=capabilities,
        providers=providers,
        bindings=bindings,
        aliases=aliases,
        tenant_providers=tenant_providers,
        provider_auth=provider_auth,
        provider_health=provider_health,
    )


__all__ = [
    "CapabilitySystem",
    "build_default_system",
]
