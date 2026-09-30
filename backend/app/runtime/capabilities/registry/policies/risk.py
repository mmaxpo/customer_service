from __future__ import annotations

from app.runtime.capabilities.registry.contracts import RejectedProvider

from .base import ResolutionContext
from .policy import ResolverPolicy


class RiskPolicy(ResolverPolicy):
    def apply(self, ctx: ResolutionContext) -> None:
        if ctx.request.max_risk is None:
            return

        risk_rank = {
            "safe": 1,
            "medium": 2,
            "high": 3,
        }

        kept = []

        for binding in ctx.candidates:
            if risk_rank[str(binding.risk)] > risk_rank[str(ctx.request.max_risk)]:
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="risk_exceeds_limit",
                        metadata={
                            "risk": str(binding.risk),
                            "max_risk": str(ctx.request.max_risk),
                        },
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
