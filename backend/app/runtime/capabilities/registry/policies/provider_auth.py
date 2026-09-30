from __future__ import annotations

from app.runtime.capabilities.registry.state import ProviderAuthRegistry
from app.runtime.capabilities.registry.registries import ProviderRegistry
from app.runtime.capabilities.registry.contracts import RejectedProvider
from .base import ResolutionContext
from .policy import ResolverPolicy


class ProviderAuthPolicy(ResolverPolicy):
    def __init__(
        self,
        *,
        providers: ProviderRegistry,
        provider_auth: ProviderAuthRegistry | None,
    ):
        self.providers = providers
        self.provider_auth = provider_auth

    def apply(self, ctx: ResolutionContext) -> None:
        if self.provider_auth is None or ctx.request.tenant_id is None:
            return

        kept = []
        for binding in ctx.candidates:
            provider = self.providers.get(binding.provider_id)

            if provider.requires_auth and not self.provider_auth.has_auth(
                tenant_id=ctx.request.tenant_id,
                provider_id=binding.provider_id,
            ):
                ctx.rejected.append(
                    RejectedProvider(
                        provider_id=binding.provider_id,
                        reason="missing_auth",
                    )
                )
                continue

            kept.append(binding)

        ctx.candidates = kept
