from __future__ import annotations

"""
Stable public API for the Tajeran semantic capability system.

Legacy V2 and former runtime-registry APIs are intentionally available only
from app.runtime.capabilities.registry.compatibility.
"""

from app.runtime.capabilities.registry.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityDomain,
    CapabilityProvider,
    CapabilityProviderKind,
    CapabilityResolutionRequest,
    CapabilityResolutionResult,
    CapabilityRisk,
    ProviderBinding,
    RejectedProvider,
)
from app.runtime.capabilities.registry.defaults import (
    build_default_system,
)
from app.runtime.capabilities.registry.manifests import (
    CapabilityManifestLoader,
    ManifestRegisterFn,
)
from app.runtime.capabilities.registry.registries import (
    BindingRegistry,
    CapabilityAliasRegistry,
    CapabilityRegistry,
    ProviderRegistry,
)
from app.runtime.capabilities.registry.resolution import (
    CapabilityResolver,
    ResolutionContext,
    ResolverPipeline,
    ResolverPolicy,
)
from app.runtime.capabilities.registry.state import (
    ProviderAuthRegistry,
    ProviderHealthRegistry,
    TenantProviderRegistry,
)
from app.runtime.capabilities.registry.system import (
    CapabilitySystem,
)


__all__ = [
    "CapabilitySystem",
    "build_default_system",
    "CapabilityResolver",
    "ResolverPipeline",
    "ResolutionContext",
    "ResolverPolicy",
    "CapabilityRegistry",
    "ProviderRegistry",
    "BindingRegistry",
    "CapabilityAliasRegistry",
    "TenantProviderRegistry",
    "ProviderAuthRegistry",
    "ProviderHealthRegistry",
    "CapabilityManifestLoader",
    "ManifestRegisterFn",
    "CapabilityDomain",
    "CapabilityCategory",
    "CapabilityDefinition",
    "CapabilityProvider",
    "CapabilityProviderKind",
    "ProviderBinding",
    "CapabilityResolutionRequest",
    "CapabilityResolutionResult",
    "CapabilityRisk",
    "RejectedProvider",
]
