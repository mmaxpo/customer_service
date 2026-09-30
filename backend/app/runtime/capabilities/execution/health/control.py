from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.events.publisher import (
    PlatformEventPublisher,
)
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthState,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
    normalize_user_id,
)


PROVIDER_HEALTH_OVERRIDE_SET_EVENT = (
    "runtime.capability.provider_health.override.set"
)
PROVIDER_HEALTH_OVERRIDE_CLEARED_EVENT = (
    "runtime.capability.provider_health.override.cleared"
)
PROVIDER_HEALTH_OVERRIDE_SOURCE = (
    "runtime.capabilities.health"
)


class CapabilityProviderHealthControlService:
    """
    Authenticated scoped health reads and operator overrides.

    Manual overrides affect effective health only. They do not mutate the
    legacy ProviderHealthRegistry or provider resolver.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CapabilityProviderHealthRepository(
            db
        )

    @staticmethod
    def state_to_dict(
        state,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        evaluated_at = now or datetime.now(
            timezone.utc
        )

        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(
                tzinfo=timezone.utc
            )

        override_active = bool(
            state.manual_override_state
            and (
                state.manual_override_until is None
                or state.manual_override_until
                > evaluated_at
            )
        )

        effective_state = (
            state.manual_override_state
            if override_active
            else state.current_state
        )

        return {
            "id": state.id,
            "user_id": state.user_id,
            "tenant_id": state.tenant_id,
            "capability_id": state.capability_id,
            "provider_id": state.provider_id,
            "provider_ref": state.provider_ref,
            "current_state": state.current_state,
            "effective_state": effective_state,
            "qualifying_recommendation": (
                state.qualifying_recommendation
            ),
            "qualifying_windows": (
                state.qualifying_windows
            ),
            "cooldown_until": state.cooldown_until,
            "manual_override_state": (
                state.manual_override_state
            ),
            "manual_override_reason": (
                state.manual_override_reason
            ),
            "manual_override_until": (
                state.manual_override_until
            ),
            "override_active": override_active,
            "version": state.version,
            "last_evaluated_at": (
                state.last_evaluated_at
            ),
            "created_at": state.created_at,
            "updated_at": state.updated_at,
        }

    async def list_states(
        self,
        *,
        user_id,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = await self.repo.list_states(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            limit=limit,
            offset=offset,
        )

        now = datetime.now(timezone.utc)
        return [
            self.state_to_dict(row, now=now)
            for row in rows
        ]

    async def set_override(
        self,
        *,
        user_id,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        override_state: ProviderHealthState,
        reason: str,
        override_until: datetime | None,
    ) -> dict[str, Any]:
        normalized_user_id = normalize_user_id(
            user_id
        )
        now = datetime.now(timezone.utc)

        normalized_until = override_until
        if (
            normalized_until is not None
            and normalized_until.tzinfo is None
        ):
            normalized_until = (
                normalized_until.replace(
                    tzinfo=timezone.utc
                )
            )

        if (
            normalized_until is not None
            and normalized_until <= now
        ):
            raise ValueError(
                "override_until must be in the future"
            )

        state = await self.repo.set_manual_override(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            override_state=override_state,
            reason=reason.strip(),
            override_until=normalized_until,
        )

        await PlatformEventPublisher(
            self.db
        ).publish(
            user_id=normalized_user_id,
            event_type=(
                PROVIDER_HEALTH_OVERRIDE_SET_EVENT
            ),
            source=PROVIDER_HEALTH_OVERRIDE_SOURCE,
            payload={
                "state_id": str(state.id),
                "tenant_id": tenant_id,
                "capability_id": capability_id,
                "provider_id": provider_id,
                "provider_ref": provider_ref,
                "override_state": (
                    override_state.value
                ),
                "reason": reason.strip(),
                "override_until": (
                    normalized_until.isoformat()
                    if normalized_until is not None
                    else None
                ),
                "state_version": state.version,
            },
            dispatch=True,
        )

        return self.state_to_dict(state, now=now)

    async def clear_override(
        self,
        *,
        user_id,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
    ) -> dict[str, Any] | None:
        normalized_user_id = normalize_user_id(
            user_id
        )

        existing = await self.repo.get_state(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        previous_override = (
            existing.manual_override_state
            if existing is not None
            else None
        )
        previous_reason = (
            existing.manual_override_reason
            if existing is not None
            else None
        )

        state = await self.repo.clear_manual_override(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        if state is None:
            return None

        await PlatformEventPublisher(
            self.db
        ).publish(
            user_id=normalized_user_id,
            event_type=(
                PROVIDER_HEALTH_OVERRIDE_CLEARED_EVENT
            ),
            source=PROVIDER_HEALTH_OVERRIDE_SOURCE,
            payload={
                "state_id": str(state.id),
                "tenant_id": tenant_id,
                "capability_id": capability_id,
                "provider_id": provider_id,
                "provider_ref": provider_ref,
                "previous_override_state": (
                    previous_override
                ),
                "previous_override_reason": (
                    previous_reason
                ),
                "state_version": state.version,
            },
            dispatch=True,
        )

        return self.state_to_dict(state)


__all__ = [
    "CapabilityProviderHealthControlService",
    "PROVIDER_HEALTH_OVERRIDE_CLEARED_EVENT",
    "PROVIDER_HEALTH_OVERRIDE_SET_EVENT",
    "PROVIDER_HEALTH_OVERRIDE_SOURCE",
]
