from __future__ import annotations

from app.runtime.capabilities.registry.state import (
    TenantProviderRegistry,
)
from app.runtime.capabilities.registry.contracts import RejectedProvider

from .base import ResolutionContext
from .policy import ResolverPolicy


class TenantAvailabilityPolicy(ResolverPolicy):
    def __init__(self, tenant_providers: TenantProviderRegistry | None):
        self.tenant_providers = tenant_providers

    def apply(self, ctx: ResolutionContext) -> None:
        if self.tenant_providers is None or ctx.request.tenant_id is None:
            return

        kept = []

        for binding in ctx.candidates:
            if not self.tenant_providers.is_enabled(
                tenant_id=ctx.request.tenant_id,
                provider_id=binding.provider_id,
            ):
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="disabled_for_tenant",
                        metadata={"tenant_id": ctx.request.tenant_id},
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
