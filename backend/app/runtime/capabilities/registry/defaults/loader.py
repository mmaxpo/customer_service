from __future__ import annotations
from app.runtime.capabilities.registry.defaults.builders import (
    build_default_manifest_loader,
    build_default_manifest_loader_v3,
)

"""Compatibility shim for the former default-loader module."""



__all__ = [
    "build_default_manifest_loader",
    "build_default_manifest_loader_v3",
]
