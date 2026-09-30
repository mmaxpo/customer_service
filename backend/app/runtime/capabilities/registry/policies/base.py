from __future__ import annotations

from dataclasses import dataclass, field

from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
    RejectedProvider,
)


@dataclass
class ResolutionContext:
    request: CapabilityResolutionRequest
    candidates: list[ProviderBinding]

    rejected: list[RejectedProvider] = field(default_factory=list)
    selected: ProviderBinding | None = None
