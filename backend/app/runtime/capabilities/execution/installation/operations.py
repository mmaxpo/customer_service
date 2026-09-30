from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.installation.repository import (
    CapabilityProviderInstallationRepository,
)


class CapabilityProviderInstallationOperations:
    """
    Transaction boundary for provider-installation mutations.

    Collaborators are injected so Runtime does not depend on a
    product-domain Shopify implementation.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: CapabilityProviderInstallationRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            if repository is not None
            else CapabilityProviderInstallationRepository(db)
        )

    async def set_enabled(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        provider_id: str,
        enabled: bool,
        lifecycle_events: Any,
    ) -> Any | None:
        row = await self.repository.set_enabled(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
            enabled=enabled,
        )

        if row is None:
            await self.db.rollback()
            return None

        await lifecycle_events.enabled_changed(
            user_id=user_id,
            installation=row,
        )

        await self.db.commit()
        await self.db.refresh(row)

        return row

    async def reconcile(
        self,
        *,
        user_id: Any,
        connections: list[Any],
        projector: Any,
        lifecycle_events: Any,
    ) -> list[Any]:
        rows = await projector.reconcile_active_connections(
            user_id=user_id,
            connections=connections,
        )

        await lifecycle_events.reconciled(
            user_id=user_id,
            installations=rows,
            discovered=len(connections),
        )

        await self.db.commit()

        for row in rows:
            await self.db.refresh(row)

        return rows


__all__ = [
    "CapabilityProviderInstallationOperations",
]
