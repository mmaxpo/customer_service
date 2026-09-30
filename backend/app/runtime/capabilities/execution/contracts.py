from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.runtime.capabilities.models import CapabilityInvocation
from app.runtime.capabilities.registry import (
    CapabilityResolutionResult,
)


@dataclass(frozen=True)
class CapabilityExecutionContext:
    """
    Stable execution context passed to a selected provider executor.

    Resolution decides which provider_ref should execute. The executor receives
    the original invocation, canonical resolution result, and runtime services
    needed to perform the actual operation.
    """

    invocation: CapabilityInvocation
    resolution: CapabilityResolutionResult
    services: Any


CapabilityExecutor = Callable[
    [CapabilityExecutionContext],
    Awaitable[Any],
]


__all__ = [
    "CapabilityExecutionContext",
    "CapabilityExecutor",
]
