from __future__ import annotations

from app.runtime.capabilities.registry.contracts import RejectedProvider

from .base import ResolutionContext
from .policy import ResolverPolicy


class LatencyPolicy(ResolverPolicy):
    def apply(self, ctx: ResolutionContext) -> None:
        if ctx.request.max_latency_ms is None:
            return

        kept = []

        for binding in ctx.candidates:
            binding_latency_ms = binding.metadata.get("latency_ms")

            if (
                binding_latency_ms is not None
                and int(binding_latency_ms) > int(ctx.request.max_latency_ms)
            ):
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="latency_exceeds_limit",
                        metadata={
                            "latency_ms": binding_latency_ms,
                            "max_latency_ms": ctx.request.max_latency_ms,
                        },
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
