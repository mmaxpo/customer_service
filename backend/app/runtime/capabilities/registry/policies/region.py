from __future__ import annotations

from app.runtime.capabilities.registry.contracts import RejectedProvider

from .base import ResolutionContext
from .policy import ResolverPolicy


class RegionPolicy(ResolverPolicy):
    def apply(self, ctx: ResolutionContext) -> None:
        if ctx.request.required_region is None:
            return

        kept = []

        for binding in ctx.candidates:
            provider_regions = tuple(binding.metadata.get("regions") or ())

            if provider_regions and ctx.request.required_region not in provider_regions:
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="region_not_supported",
                        metadata={
                            "required_region": ctx.request.required_region,
                            "provider_regions": list(provider_regions),
                        },
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
