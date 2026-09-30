from __future__ import annotations

from app.runtime.capabilities.registry.contracts import RejectedProvider

from .base import ResolutionContext
from .policy import ResolverPolicy


class SelectionPolicy(ResolverPolicy):
    def apply(self, ctx: ResolutionContext) -> None:
        if not ctx.candidates:
            ctx.selected = None
            return

        preferred_provider_id = ctx.request.preferred_provider_id

        if preferred_provider_id:
            ctx.selected = next(
                (
                    binding
                    for binding in ctx.candidates
                    if binding.provider_id == preferred_provider_id
                ),
                None,
            )

        if ctx.selected is None:
            ctx.selected = sorted(
                ctx.candidates,
                key=lambda binding: (
                    -binding.priority,
                    binding.provider_id,
                ),
            )[0]

        for binding in ctx.candidates:
            if binding is ctx.selected:
                continue

            ctx.rejected.append(
                RejectedProvider(
                    provider_id=binding.provider_id,
                    reason="lower_priority",
                    metadata={
                        "priority": binding.priority,
                        "selected_provider_id": ctx.selected.provider_id,
                        "selected_priority": ctx.selected.priority,
                    },
                )
            )
