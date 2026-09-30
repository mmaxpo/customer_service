from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityProviderInstallationRecord,
)
from app.runtime.capabilities.execution.installation.models import (
    ProviderAuthenticationState,
    ProviderConfigurationState,
    ProviderInstallationReader,
    ProviderInstallationScope,
    ProviderInstallationSnapshot,
    ProviderInstallationUpsert,
    ProviderVerificationState,
)


def normalize_installation_user_id(
    value: Any,
) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        raise ValueError(
            "user_id must be a valid UUID"
        ) from exc


class CapabilityProviderInstallationRepository:
    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def get(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        provider_id: str,
    ) -> CapabilityProviderInstallationRecord | None:
        scope = ProviderInstallationScope(
            user_id=normalize_installation_user_id(
                user_id
            ),
            tenant_id=tenant_id,
            provider_id=provider_id,
        )

        result = await self.db.execute(
            select(
                CapabilityProviderInstallationRecord
            ).where(
                CapabilityProviderInstallationRecord
                .scope_key
                == scope.scope_key()
            )
        )

        record = result.scalar_one_or_none()

        if (
            record is not None
            or scope.tenant_id is None
        ):
            return record

        # Domain integrations such as the current Shopify connection are
        # user-owned rather than tenant-owned. A tenant-scoped runtime may
        # therefore consume the authenticated user's global installation when
        # no tenant-specific override exists.
        global_scope = ProviderInstallationScope(
            user_id=scope.user_id,
            tenant_id=None,
            provider_id=scope.provider_id,
        )

        result = await self.db.execute(
            select(
                CapabilityProviderInstallationRecord
            ).where(
                CapabilityProviderInstallationRecord
                .scope_key
                == global_scope.scope_key()
            )
        )

        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        user_id: Any,
        tenant_id: str | None = None,
        provider_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[
        CapabilityProviderInstallationRecord
    ]:
        normalized_user_id = (
            normalize_installation_user_id(
                user_id
            )
        )

        stmt = (
            select(
                CapabilityProviderInstallationRecord
            )
            .where(
                CapabilityProviderInstallationRecord
                .user_id
                == normalized_user_id
            )
            .order_by(
                CapabilityProviderInstallationRecord
                .updated_at
                .desc(),
                CapabilityProviderInstallationRecord
                .provider_id
                .asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        if tenant_id is not None:
            stmt = stmt.where(
                CapabilityProviderInstallationRecord
                .tenant_id
                == tenant_id
            )

        if provider_id is not None:
            stmt = stmt.where(
                CapabilityProviderInstallationRecord
                .provider_id
                == provider_id
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_exact(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        provider_id: str,
    ) -> (
        CapabilityProviderInstallationRecord
        | None
    ):
        scope = ProviderInstallationScope(
            user_id=(
                normalize_installation_user_id(
                    user_id
                )
            ),
            tenant_id=tenant_id,
            provider_id=provider_id,
        )

        result = await self.db.execute(
            select(
                CapabilityProviderInstallationRecord
            ).where(
                CapabilityProviderInstallationRecord
                .scope_key
                == scope.scope_key()
            )
        )

        return result.scalar_one_or_none()

    async def set_enabled(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        provider_id: str,
        enabled: bool,
    ) -> (
        CapabilityProviderInstallationRecord
        | None
    ):
        row = await self.get_exact(
            user_id=user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
        )

        if row is None:
            return None

        row.enabled = bool(enabled)
        row.version += 1
        row.updated_at = datetime.now(
            timezone.utc
        )

        await self.db.flush()
        await self.db.refresh(row)

        return row

    async def upsert(
        self,
        *,
        scope: ProviderInstallationScope,
        installation: ProviderInstallationUpsert,
    ) -> CapabilityProviderInstallationRecord:
        now = datetime.now(timezone.utc)

        verified_at = (
            now
            if installation.verification_state
            == ProviderVerificationState.VERIFIED
            else None
        )

        await self.db.execute(
            insert(
                CapabilityProviderInstallationRecord
            )
            .values(
                scope_key=scope.scope_key(),
                user_id=scope.user_id,
                tenant_id=scope.tenant_id,
                provider_id=scope.provider_id,
                integration_kind=(
                    installation.integration_kind
                ),
                integration_connection_id=(
                    installation
                    .integration_connection_id
                ),
                enabled=installation.enabled,
                configuration_state=(
                    installation
                    .configuration_state
                    .value
                ),
                authentication_state=(
                    installation
                    .authentication_state
                    .value
                ),
                verification_state=(
                    installation
                    .verification_state
                    .value
                ),
                verified_at=verified_at,
                failure_code=(
                    installation.failure_code
                ),
                failure_message=(
                    installation.failure_message
                ),
                version=1,
                metadata_json=installation.metadata,
            )
            .on_conflict_do_update(
                index_elements=[
                    CapabilityProviderInstallationRecord
                    .scope_key
                ],
                set_={
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
                        .value
                    ),
                    "authentication_state": (
                        installation
                        .authentication_state
                        .value
                    ),
                    "verification_state": (
                        installation
                        .verification_state
                        .value
                    ),
                    "verified_at": verified_at,
                    "failure_code": (
                        installation.failure_code
                    ),
                    "failure_message": (
                        installation.failure_message
                    ),
                    "metadata_json": (
                        installation.metadata
                    ),
                    "version": (
                        CapabilityProviderInstallationRecord
                        .version
                        + 1
                    ),
                    "updated_at": now,
                },
            )
        )

        result = await self.db.execute(
            select(
                CapabilityProviderInstallationRecord
            )
            .where(
                CapabilityProviderInstallationRecord
                .scope_key
                == scope.scope_key()
            )
            .execution_options(
                populate_existing=True
            )
        )

        return result.scalar_one()


class DatabaseProviderInstallationReader(ProviderInstallationReader):
    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.repo = (
            CapabilityProviderInstallationRepository(
                db
            )
        )

    async def get_provider_installation(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        provider_id: str,
    ) -> ProviderInstallationSnapshot:
        try:
            normalized_user_id = (
                normalize_installation_user_id(
                    user_id
                )
            )
        except ValueError:
            return ProviderInstallationSnapshot(
                found=False,
                user_id=None,
                tenant_id=tenant_id,
                provider_id=provider_id,
                metadata={
                    "reason": "invalid_user_id"
                },
            )

        row = await self.repo.get(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            provider_id=provider_id,
        )

        if row is None:
            return ProviderInstallationSnapshot(
                found=False,
                user_id=str(normalized_user_id),
                tenant_id=tenant_id,
                provider_id=provider_id,
                enabled=False,
                configuration_state=(
                    ProviderConfigurationState
                    .UNCONFIGURED
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
                    "reason": (
                        "provider_installation_not_found"
                    )
                },
            )

        return ProviderInstallationSnapshot(
            found=True,
            user_id=str(row.user_id),
            tenant_id=row.tenant_id,
            provider_id=row.provider_id,
            enabled=row.enabled,
            configuration_state=(
                ProviderConfigurationState(
                    row.configuration_state
                )
            ),
            authentication_state=(
                ProviderAuthenticationState(
                    row.authentication_state
                )
            ),
            verification_state=(
                ProviderVerificationState(
                    row.verification_state
                )
            ),
            integration_kind=(
                row.integration_kind
            ),
            integration_connection_id=(
                row.integration_connection_id
            ),
            failure_code=row.failure_code,
            failure_message=row.failure_message,
            version=row.version,
            metadata=dict(
                row.metadata_json or {}
            ),
        )


__all__ = [
    "CapabilityProviderInstallationRepository",
    "DatabaseProviderInstallationReader",
    "normalize_installation_user_id",
]
