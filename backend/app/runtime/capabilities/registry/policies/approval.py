from __future__ import annotations

from app.runtime.capabilities.registry.contracts import RejectedProvider

from .base import ResolutionContext
from .policy import ResolverPolicy


class ApprovalPolicy(ResolverPolicy):
    def apply(self, ctx: ResolutionContext) -> None:
        if ctx.request.allow_approval_required:
            return

        kept = []

        for binding in ctx.candidates:
            if binding.requires_approval:
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="approval_required",
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
