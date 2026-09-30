from __future__ import annotations

from app.runtime.objectives.resolution.registry import (
    ObjectiveResolutionAdapterRegistry,
)


def build_default_objective_resolution_registry(
) -> ObjectiveResolutionAdapterRegistry:
    """
    Build the product-neutral default registry.

    Product composition roots may register their adapters
    explicitly. Core defaults never import product domains.
    """

    return ObjectiveResolutionAdapterRegistry()


__all__ = [
    "build_default_objective_resolution_registry",
]
