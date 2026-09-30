from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.shopify import (
    ShopifyService,
)
from app.runtime.capabilities.execution.installation.verification import (
    ProviderInstallationVerifierRegistry,
)


class ShopifyProviderVerifier:
    """Verify Shopify using the existing Shopify service lifecycle."""

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self._service = ShopifyService(
            db
        )

    async def verify(
        self,
        *,
        user_id: Any,
    ) -> dict[str, Any]:
        return await self._service.test_connection(
            user_id=user_id
        )


def register_shopify_provider_verifier(
    registry: ProviderInstallationVerifierRegistry,
    *,
    db: AsyncSession,
) -> None:
    registry.register(
        "shopify",
        ShopifyProviderVerifier(
            db
        ),
    )


__all__ = [
    "ShopifyProviderVerifier",
    "register_shopify_provider_verifier",
]
