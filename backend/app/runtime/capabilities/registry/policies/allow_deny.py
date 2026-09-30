from __future__ import annotations

from app.runtime.capabilities.registry.contracts import (
    RejectedProvider,
)

from .base import ResolutionContext
from .policy import ResolverPolicy


class AllowDenyPolicy(ResolverPolicy):
    def apply(
        self,
        ctx: ResolutionContext,
    ) -> None:

        kept = []

        for binding in ctx.candidates:

            if (
                ctx.request.allowed_provider_ids
                and binding.provider_id not in ctx.request.allowed_provider_ids
            ):
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="not_in_allowed_providers",
                        metadata={
                            "allowed_provider_ids": list(
                                ctx.request.allowed_provider_ids
                            )
                        },
                    )
                )
                continue

            if binding.provider_id in ctx.request.denied_provider_ids:
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="provider_denied",
                        metadata={
                            "denied_provider_ids": list(
                                ctx.request.denied_provider_ids
                            )
                        },
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
