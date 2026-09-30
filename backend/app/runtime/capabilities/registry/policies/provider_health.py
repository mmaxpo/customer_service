from __future__ import annotations

from app.runtime.capabilities.registry.state import ProviderHealthRegistry
from app.runtime.capabilities.registry.contracts import RejectedProvider
from .base import ResolutionContext
from .policy import ResolverPolicy


class ProviderHealthPolicy(ResolverPolicy):
    def __init__(self, provider_health: ProviderHealthRegistry | None):
        self.provider_health = provider_health

    def apply(self, ctx: ResolutionContext) -> None:
        if self.provider_health is None:
            return

        kept = []
        for binding in ctx.candidates:
            if not self.provider_health.is_healthy(binding.provider_id):
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="provider_unhealthy",
                    )
                )
                continue
            kept.append(binding)

        ctx.candidates = kept
