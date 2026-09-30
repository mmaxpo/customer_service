from __future__ import annotations

"""Compatibility shim for the former default-loader module."""

from app.runtime.capabilities.registry.defaults.builders import (
    build_default_manifest_loader,
    build_default_manifest_loader_v3,
)


__all__ = [
    "build_default_manifest_loader",
    "build_default_manifest_loader_v3",
]
