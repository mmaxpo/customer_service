from __future__ import annotations

from app.runtime.capabilities.registry.contracts import (
    RejectedProvider,
)

from .base import ResolutionContext
from .policy import ResolverPolicy


class CostPolicy(ResolverPolicy):
    def apply(
        self,
        ctx: ResolutionContext,
    ) -> None:
        if ctx.request.max_cost is None:
            return

        kept = []

        for binding in ctx.candidates:
            binding_cost = binding.metadata.get("cost")

            if (
                binding_cost is not None
                and float(binding_cost) > float(ctx.request.max_cost)
            ):
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="cost_exceeds_limit",
                        metadata={
                            "cost": binding_cost,
                            "max_cost": ctx.request.max_cost,
                        },
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
