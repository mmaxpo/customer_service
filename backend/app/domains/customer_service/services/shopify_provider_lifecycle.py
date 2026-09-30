from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.events.publisher import (
    PlatformEventPublisher,
)


SHOPIFY_INSTALLATION_CONNECTED_EVENT = (
    "runtime.provider.installation.connected"
)
SHOPIFY_INSTALLATION_VERIFIED_EVENT = (
    "runtime.provider.installation.verified"
)
SHOPIFY_INSTALLATION_VERIFICATION_FAILED_EVENT = (
    "runtime.provider.installation."
    "verification_failed"
)
SHOPIFY_INSTALLATION_DISABLED_EVENT = (
    "runtime.provider.installation.disabled"
)
SHOPIFY_INSTALLATION_ENABLED_EVENT = (
    "runtime.provider.installation.enabled"
)
SHOPIFY_INSTALLATION_RECONCILED_EVENT = (
    "runtime.provider.installation.reconciled"
)

PROVIDER_INSTALLATION_EVENT_SOURCE = (
    "runtime.provider_installations"
)


class ShopifyProviderLifecycleEvents:
    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.publisher = PlatformEventPublisher(
            db
        )

    async def connected(
        self,
        *,
        user_id: Any,
        installation,
    ) -> None:
        await self._publish(
            event_type=(
                SHOPIFY_INSTALLATION_CONNECTED_EVENT
            ),
            user_id=user_id,
            installation=installation,
        )

    async def verified(
        self,
        *,
        user_id: Any,
        installation,
        shop: dict,
    ) -> None:
        await self._publish(
            event_type=(
                SHOPIFY_INSTALLATION_VERIFIED_EVENT
            ),
            user_id=user_id,
            installation=installation,
            extra={
                "shop": {
                    "id": shop.get("id"),
                    "name": shop.get("name"),
                    "myshopify_domain": (
                        shop.get(
                            "myshopify_domain"
                        )
                    ),
                },
            },
        )

    async def verification_failed(
        self,
        *,
        user_id: Any,
        installation,
    ) -> None:
        await self._publish(
            event_type=(
                SHOPIFY_INSTALLATION_VERIFICATION_FAILED_EVENT
            ),
            user_id=user_id,
            installation=installation,
        )

    async def enabled_changed(
        self,
        *,
        user_id: Any,
        installation,
    ) -> None:
        await self._publish(
            event_type=(
                SHOPIFY_INSTALLATION_ENABLED_EVENT
                if installation.enabled
                else SHOPIFY_INSTALLATION_DISABLED_EVENT
            ),
            user_id=user_id,
            installation=installation,
        )

    async def reconciled(
        self,
        *,
        user_id: Any,
        installations: list[Any],
        discovered: int,
    ) -> None:
        await self.publisher.publish(
            user_id=user_id,
            event_type=(
                SHOPIFY_INSTALLATION_RECONCILED_EVENT
            ),
            source=(
                PROVIDER_INSTALLATION_EVENT_SOURCE
            ),
            payload={
                "provider_id": "shopify",
                "discovered": discovered,
                "projected": len(
                    installations
                ),
                "installation_ids": [
                    str(row.id)
                    for row in installations
                ],
            },
            dispatch=False,
            commit=False,
        )

    async def _publish(
        self,
        *,
        event_type: str,
        user_id: Any,
        installation,
        extra: dict | None = None,
    ) -> None:
        payload = {
            "installation_id": str(
                installation.id
            ),
            "provider_id": (
                installation.provider_id
            ),
            "tenant_id": (
                installation.tenant_id
            ),
            "integration_kind": (
                installation.integration_kind
            ),
            "integration_connection_id": (
                installation
                .integration_connection_id
            ),
            "enabled": installation.enabled,
            "configuration_state": (
                installation
                .configuration_state
            ),
            "authentication_state": (
                installation
                .authentication_state
            ),
            "verification_state": (
                installation
                .verification_state
            ),
            "failure_code": (
                installation.failure_code
            ),
            "version": installation.version,
        }

        if extra:
            payload.update(extra)

        await self.publisher.publish(
            user_id=user_id,
            event_type=event_type,
            source=(
                PROVIDER_INSTALLATION_EVENT_SOURCE
            ),
            payload=payload,
            dispatch=False,
            commit=False,
        )


__all__ = [
    "PROVIDER_INSTALLATION_EVENT_SOURCE",
    "SHOPIFY_INSTALLATION_CONNECTED_EVENT",
    "SHOPIFY_INSTALLATION_DISABLED_EVENT",
    "SHOPIFY_INSTALLATION_ENABLED_EVENT",
    "SHOPIFY_INSTALLATION_RECONCILED_EVENT",
    "SHOPIFY_INSTALLATION_VERIFICATION_FAILED_EVENT",
    "SHOPIFY_INSTALLATION_VERIFIED_EVENT",
    "ShopifyProviderLifecycleEvents",
]
