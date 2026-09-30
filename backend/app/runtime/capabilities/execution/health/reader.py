from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)


class ProviderHealthSnapshot(BaseModel):
    """
    Scoped effective-health observation used by runtime resolution.

    This is intentionally a read model. It does not modify provider
    selection, durable health state, or the legacy ProviderHealthRegistry.
    """

    model_config = ConfigDict(extra="forbid")

    found: bool
    user_id: str | None = None
    tenant_id: str | None = None
    capability_id: str
    provider_id: str
    provider_ref: str | None = None

    current_state: str = "healthy"
    effective_state: str = "healthy"

    override_active: bool = False
    manual_override_state: str | None = None
    manual_override_until: datetime | None = None

    state_version: int | None = None
    observed_at: datetime


@runtime_checkable
class ProviderHealthReader(Protocol):
    async def get_effective_health(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        observed_at: datetime | None = None,
    ) -> ProviderHealthSnapshot:
        ...


class NullProviderHealthReader(ProviderHealthReader):
    """
    Safe default for runtimes without a database or authenticated owner.

    Unknown durable state is observationally healthy so shadow mode never
    changes the existing provider-selection result.
    """

    async def get_effective_health(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        observed_at: datetime | None = None,
    ) -> ProviderHealthSnapshot:
        now = _normalize_datetime(observed_at)

        return ProviderHealthSnapshot(
            found=False,
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            current_state="healthy",
            effective_state="healthy",
            observed_at=now,
        )


class DatabaseProviderHealthReader(ProviderHealthReader):
    """
    SQLAlchemy-backed scoped health reader.

    Invalid or absent user ownership returns an unknown snapshot instead of
    causing capability execution to fail. Runtime health remains shadow-only.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.repo = CapabilityProviderHealthRepository(
            db
        )
        self.null_reader = NullProviderHealthReader()

    async def get_effective_health(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        observed_at: datetime | None = None,
    ) -> ProviderHealthSnapshot:
        now = _normalize_datetime(observed_at)

        try:
            normalized_user_id = UUID(str(user_id))
        except (TypeError, ValueError, AttributeError):
            return await self.null_reader.get_effective_health(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id=capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
                observed_at=now,
            )

        state = await self.repo.get_state(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        if state is None:
            return await self.null_reader.get_effective_health(
                user_id=str(normalized_user_id),
                tenant_id=tenant_id,
                capability_id=capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
                observed_at=now,
            )

        override_active = bool(
            state.manual_override_state
            and (
                state.manual_override_until is None
                or state.manual_override_until > now
            )
        )

        effective_state = (
            state.manual_override_state
            if override_active
            else state.current_state
        )

        return ProviderHealthSnapshot(
            found=True,
            user_id=str(normalized_user_id),
            tenant_id=state.tenant_id,
            capability_id=state.capability_id,
            provider_id=state.provider_id,
            provider_ref=state.provider_ref,
            current_state=state.current_state,
            effective_state=effective_state,
            override_active=override_active,
            manual_override_state=(
                state.manual_override_state
            ),
            manual_override_until=(
                state.manual_override_until
            ),
            state_version=state.version,
            observed_at=now,
        )


def _normalize_datetime(
    value: datetime | None,
) -> datetime:
    result = value or datetime.now(timezone.utc)

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result.astimezone(timezone.utc)


__all__ = [
    "DatabaseProviderHealthReader",
    "NullProviderHealthReader",
    "ProviderHealthReader",
    "ProviderHealthSnapshot",
]
