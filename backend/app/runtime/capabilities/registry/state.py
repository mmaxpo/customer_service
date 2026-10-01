from __future__ import annotations
from dataclasses import dataclass, field

"""
Canonical dynamic-state implementations for capability resolution.

This module owns tenant provider availability, provider authentication state,
and provider health state. Historical module paths remain compatibility shims.
"""



@dataclass
class TenantProviderRegistry:
    _enabled: dict[tuple[str, str], bool] = field(default_factory=dict)

    def register_provider(
        self,
        *,
        tenant_id: str,
        provider_id: str,
        enabled: bool = True,
    ) -> None:
        tenant_id = str(tenant_id or "").strip()
        provider_id = str(provider_id or "").strip()

        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")
        if not provider_id:
            raise ValueError("provider_id cannot be empty")

        self._enabled[(tenant_id, provider_id)] = enabled

    def enable(self, *, tenant_id: str, provider_id: str) -> None:
        self.register_provider(
            tenant_id=tenant_id,
            provider_id=provider_id,
            enabled=True,
        )

    def disable(self, *, tenant_id: str, provider_id: str) -> None:
        self.register_provider(
            tenant_id=tenant_id,
            provider_id=provider_id,
            enabled=False,
        )

    def is_enabled(self, *, tenant_id: str | None, provider_id: str) -> bool:
        if tenant_id is None:
            return True

        tenant_id = str(tenant_id or "").strip()
        provider_id = str(provider_id or "").strip()

        if not tenant_id:
            return True

        return self._enabled.get((tenant_id, provider_id), False)

    def list_enabled(self, *, tenant_id: str) -> list[str]:
        tenant_id = str(tenant_id or "").strip()
        return sorted(
            provider_id
            for (item_tenant_id, provider_id), enabled in self._enabled.items()
            if item_tenant_id == tenant_id and enabled
        )




@dataclass
class ProviderAuthRegistry:
    _auth: dict[tuple[str, str], bool] = field(default_factory=dict)

    def connect(
        self,
        *,
        tenant_id: str,
        provider_id: str,
    ) -> None:
        self._auth[(tenant_id, provider_id)] = True

    def disconnect(
        self,
        *,
        tenant_id: str,
        provider_id: str,
    ) -> None:
        self._auth[(tenant_id, provider_id)] = False

    def has_auth(
        self,
        *,
        tenant_id: str | None,
        provider_id: str,
    ) -> bool:
        if tenant_id is None:
            return True

        return self._auth.get((tenant_id, provider_id), False)




@dataclass
class ProviderHealthRegistry:
    _healthy: dict[str, bool] = field(default_factory=dict)

    def mark_healthy(self, provider_id: str) -> None:
        provider_id = str(provider_id or "").strip()
        if not provider_id:
            raise ValueError("provider_id cannot be empty")
        self._healthy[provider_id] = True

    def mark_unhealthy(self, provider_id: str) -> None:
        provider_id = str(provider_id or "").strip()
        if not provider_id:
            raise ValueError("provider_id cannot be empty")
        self._healthy[provider_id] = False

    def is_healthy(self, provider_id: str) -> bool:
        provider_id = str(provider_id or "").strip()
        if not provider_id:
            return False
        return self._healthy.get(provider_id, True)


__all__ = [
    "TenantProviderRegistry",
    "ProviderAuthRegistry",
    "ProviderHealthRegistry",
]
