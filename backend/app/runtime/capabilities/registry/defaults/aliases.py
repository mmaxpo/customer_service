from __future__ import annotations
from app.runtime.capabilities.registry.defaults.builders import (
    build_default_capability_alias_registry,
    build_default_capability_alias_registry_v3,
)

"""Compatibility shim for the former alias-default builder module."""



__all__ = [
    "build_default_capability_alias_registry",
    "build_default_capability_alias_registry_v3",
]
