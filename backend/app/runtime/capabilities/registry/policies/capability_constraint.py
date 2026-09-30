from __future__ import annotations

from app.runtime.capabilities.registry.contracts import (
    RejectedProvider,
)

from .base import ResolutionContext
from .policy import ResolverPolicy


class CapabilityConstraintPolicy(ResolverPolicy):
    def apply(
        self,
        ctx: ResolutionContext,
    ) -> None:

        if ctx.request.required_action is None:
            return

        kept = []

        for binding in ctx.candidates:

            supported_actions = tuple(
                binding.metadata.get("supported_actions") or ()
            )

            if (
                supported_actions
                and ctx.request.required_action not in supported_actions
            ):
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="action_not_supported",
                        metadata={
                            "required_action": ctx.request.required_action,
                            "supported_actions": list(supported_actions),
                        },
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
