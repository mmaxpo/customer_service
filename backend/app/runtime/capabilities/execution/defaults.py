from __future__ import annotations

from app.runtime.capabilities.execution.providers.shopify import (
    register_shopify_executors,
)
from app.runtime.capabilities.execution.registry import (
    CapabilityExecutorRegistry,
)


def build_default_executor_registry() -> CapabilityExecutorRegistry:
    registry = CapabilityExecutorRegistry()
    register_shopify_executors(registry)
    return registry


__all__ = ["build_default_executor_registry"]
