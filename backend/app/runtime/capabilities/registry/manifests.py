from __future__ import annotations

"""
Canonical provider-manifest loading implementation.

Provider packages contribute domains, categories, capabilities, providers,
bindings, and compatibility aliases through this loader. The historical
manifest_loader.py path remains a compatibility shim.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.runtime.capabilities.registry.registries import BindingRegistry
from app.runtime.capabilities.registry.registries import CapabilityRegistry
from app.runtime.capabilities.registry.registries import CapabilityAliasRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry

ManifestRegisterFn = Callable[..., None]


@dataclass
class CapabilityManifestLoader:
    manifests: list[ManifestRegisterFn] = field(default_factory=list)

    def register_manifest(self, manifest: ManifestRegisterFn) -> None:
        self.manifests.append(manifest)

    def load(
        self,
        *,
        capabilities: CapabilityRegistry,
        providers: ProviderRegistry,
        bindings: BindingRegistry,
        aliases: CapabilityAliasRegistry,
    ) -> None:
        for manifest in self.manifests:
            manifest(
                capabilities=capabilities,
                providers=providers,
                bindings=bindings,
                aliases=aliases,
            )


__all__ = [
    "ManifestRegisterFn",
    "CapabilityManifestLoader",
]
