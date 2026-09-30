from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.installation.models import (
    ProviderAuthenticationState,
    ProviderConfigurationState,
    ProviderInstallationScope,
    ProviderInstallationUpsert,
    ProviderVerificationState,
)
from app.runtime.capabilities.execution.installation.repository import (
    CapabilityProviderInstallationRepository,
)


class ShopifyProviderInstallationProjector:
    """
    Project Shopify-owned connection state into semantic provider availability.

    Shopify remains the source of truth for its encrypted token and shop
    domain. This projection stores only non-secret runtime availability state.
    """

    PROVIDER_ID = "shopify"
    INTEGRATION_KIND = "shopify"

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db
        self.repo = (
            CapabilityProviderInstallationRepository(
                db
            )
        )

    async def reconcile_active_connections(
        self,
        *,
        user_id: Any,
        connections: list[Any],
    ) -> list[Any]:
        rows = []

        for connection in connections:
            rows.append(
                await self.project_connected(
                    user_id=user_id,
                    connection_id=connection.id,
                    shop_domain=(
                        connection.shop_domain
                    ),
                    has_access_token=bool(
                        connection
                        .access_token_encrypted
                    ),
                )
            )

        return rows

    async def project_connected(
        self,
        *,
        user_id: Any,
        connection_id: Any,
        shop_domain: str,
        has_access_token: bool,
    ):
        return await self.repo.upsert(
            scope=self._scope(user_id),
            installation=ProviderInstallationUpsert(
                integration_kind=(
                    self.INTEGRATION_KIND
                ),
                integration_connection_id=(
                    str(connection_id)
                ),
                enabled=True,
                configuration_state=(
                    ProviderConfigurationState
                    .CONFIGURED
                ),
                authentication_state=(
                    ProviderAuthenticationState
                    .AUTHENTICATED
                    if has_access_token
                    else ProviderAuthenticationState
                    .MISSING
                ),
                verification_state=(
                    ProviderVerificationState
                    .UNVERIFIED
                ),
                metadata={
                    "shop_domain": shop_domain,
                },
            ),
        )

    async def project_verified(
        self,
        *,
        user_id: Any,
        connection_id: Any,
        shop_domain: str,
    ):
        return await self.repo.upsert(
            scope=self._scope(user_id),
            installation=ProviderInstallationUpsert(
                integration_kind=(
                    self.INTEGRATION_KIND
                ),
                integration_connection_id=(
                    str(connection_id)
                ),
                enabled=True,
                configuration_state=(
                    ProviderConfigurationState
                    .CONFIGURED
                ),
                authentication_state=(
                    ProviderAuthenticationState
                    .AUTHENTICATED
                ),
                verification_state=(
                    ProviderVerificationState
                    .VERIFIED
                ),
                metadata={
                    "shop_domain": shop_domain,
                },
            ),
        )

    async def project_verification_failed(
        self,
        *,
        user_id: Any,
        connection_id: Any,
        shop_domain: str,
        failure_message: str,
    ):
        return await self.repo.upsert(
            scope=self._scope(user_id),
            installation=ProviderInstallationUpsert(
                integration_kind=(
                    self.INTEGRATION_KIND
                ),
                integration_connection_id=(
                    str(connection_id)
                ),
                enabled=True,
                configuration_state=(
                    ProviderConfigurationState
                    .CONFIGURED
                ),
                authentication_state=(
                    ProviderAuthenticationState
                    .INVALID
                ),
                verification_state=(
                    ProviderVerificationState
                    .FAILED
                ),
                failure_code=(
                    "shopify_connection_test_failed"
                ),
                failure_message=(
                    failure_message
                ),
                metadata={
                    "shop_domain": shop_domain,
                },
            ),
        )

    async def project_disconnected(
        self,
        *,
        user_id: Any,
        connection_id: Any,
        shop_domain: str,
    ):
        return await self.repo.upsert(
            scope=self._scope(user_id),
            installation=ProviderInstallationUpsert(
                integration_kind=(
                    self.INTEGRATION_KIND
                ),
                integration_connection_id=(
                    str(connection_id)
                ),
                enabled=False,
                configuration_state=(
                    ProviderConfigurationState
                    .CONFIGURED
                ),
                authentication_state=(
                    ProviderAuthenticationState
                    .MISSING
                ),
                verification_state=(
                    ProviderVerificationState
                    .UNVERIFIED
                ),
                metadata={
                    "shop_domain": shop_domain,
                },
            ),
        )

    @classmethod
    def _scope(
        cls,
        user_id: Any,
    ) -> ProviderInstallationScope:
        return ProviderInstallationScope(
            user_id=user_id,
            tenant_id=None,
            provider_id=cls.PROVIDER_ID,
        )


__all__ = [
    "ShopifyProviderInstallationProjector",
]
