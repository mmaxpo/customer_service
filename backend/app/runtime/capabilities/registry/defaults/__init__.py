from __future__ import annotations

from app.runtime.capabilities.registry.defaults.builders import (
    build_default_binding_registry,
    build_default_binding_registry_v3,
    build_default_capability_alias_registry,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry,
    build_default_capability_registry_v3,
    build_default_manifest_loader,
    build_default_manifest_loader_v3,
    build_default_provider_registry,
    build_default_provider_registry_v3,
    build_default_system,
)


__all__ = [
    "build_default_system",
    "build_default_manifest_loader",
    "build_default_capability_registry",
    "build_default_provider_registry",
    "build_default_binding_registry",
    "build_default_capability_alias_registry",

    # Temporary compatibility exports.
    "build_default_manifest_loader_v3",
    "build_default_capability_registry_v3",
    "build_default_provider_registry_v3",
    "build_default_binding_registry_v3",
    "build_default_capability_alias_registry_v3",
]
