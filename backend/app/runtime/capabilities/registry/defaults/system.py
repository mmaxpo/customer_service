from __future__ import annotations

"""Compatibility shim for the former default-system builder module."""

from app.runtime.capabilities.registry.defaults.builders import (
    build_default_system,
)


__all__ = [
    "build_default_system",
]
