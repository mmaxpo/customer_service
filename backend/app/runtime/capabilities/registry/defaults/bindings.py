from __future__ import annotations

"""Compatibility shim for the former binding-default builder module."""

from app.runtime.capabilities.registry.defaults.builders import (
    build_default_binding_registry,
    build_default_binding_registry_v3,
)


__all__ = [
    "build_default_binding_registry",
    "build_default_binding_registry_v3",
]
