from __future__ import annotations

from app.runtime.capabilities.registry.contracts import RejectedProvider

from .base import ResolutionContext
from .policy import ResolverPolicy


class BindingEnabledPolicy(ResolverPolicy):
    def apply(self, ctx: ResolutionContext) -> None:
        kept = []

        for binding in ctx.candidates:
            if not binding.enabled:
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="disabled",
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
