from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityProviderHealthProbeResultRecord,
    CapabilityProviderHealthStateRecord,
)
from app.runtime.capabilities.execution.health.repository import (
    build_provider_health_scope_key,
)


class ProviderHealthProbeClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acquired: bool
    reason: str

    scope_key: str | None = None
    lease_token: str | None = None
    lease_until: datetime | None = None
    claimed_at: datetime

    current_state: str | None = None
    manual_override_active: bool = False
    cooldown_until: datetime | None = None


class ProviderHealthProbeCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completed: bool
    duplicate: bool = False
    reason: str

    scope_key: str | None = None
    lease_token: str

    succeeded: bool
    previous_state: str | None = None
    resulting_state: str | None = None

    cooldown_until: datetime | None = None
    completed_at: datetime

    result_id: str | None = None
    state_version: int | None = None


@runtime_checkable
class ProviderHealthProbeCoordinator(Protocol):
    async def try_claim_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        observed_at: datetime | None = None,
        lease_seconds: int = 60,
    ) -> ProviderHealthProbeClaim: ...

    async def complete_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        lease_token: str,
        succeeded: bool,
        completed_at: datetime | None = None,
        failure_cooldown_seconds: int = 300,
        failure_kind: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderHealthProbeCompletion: ...


class NullProviderHealthProbeCoordinator:
    """
    Safe default when no durable database coordinator is available.

    Probe admission fails closed: an unhealthy provider remains rejected.
    """

    async def try_claim_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        observed_at: datetime | None = None,
        lease_seconds: int = 60,
    ) -> ProviderHealthProbeClaim:
        now = _normalize_datetime(observed_at)

        return ProviderHealthProbeClaim(
            acquired=False,
            reason="probe_coordinator_unavailable",
            claimed_at=now,
        )

    async def complete_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        lease_token: str,
        succeeded: bool,
        completed_at: datetime | None = None,
        failure_cooldown_seconds: int = 300,
        failure_kind: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderHealthProbeCompletion:
        now = _normalize_datetime(completed_at)

        return ProviderHealthProbeCompletion(
            completed=False,
            reason="probe_coordinator_unavailable",
            lease_token=lease_token,
            succeeded=succeeded,
            completed_at=now,
        )


class IsolatedDatabaseProviderHealthProbeCoordinator:
    """
    Open a dedicated database session for every health mutation.

    Capability and request transactions must never be committed or rolled
    back by provider-health lease admission or completion. The delegated
    coordinator owns only the short-lived session created here.
    """

    def __init__(self, session_factory: Any) -> None:
        if session_factory is None:
            raise ValueError(
                "health probe session_factory is required"
            )

        self.session_factory = session_factory

    async def try_claim_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        observed_at: datetime | None = None,
        lease_seconds: int = 60,
    ) -> ProviderHealthProbeClaim:
        async with self.session_factory() as db:
            return await (
                DatabaseProviderHealthProbeCoordinator(
                    db
                ).try_claim_probe(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    capability_id=capability_id,
                    provider_id=provider_id,
                    provider_ref=provider_ref,
                    observed_at=observed_at,
                    lease_seconds=lease_seconds,
                )
            )

    async def complete_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        lease_token: str,
        succeeded: bool,
        completed_at: datetime | None = None,
        failure_cooldown_seconds: int = 300,
        failure_kind: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderHealthProbeCompletion:
        async with self.session_factory() as db:
            return await (
                DatabaseProviderHealthProbeCoordinator(
                    db
                ).complete_probe(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    capability_id=capability_id,
                    provider_id=provider_id,
                    provider_ref=provider_ref,
                    lease_token=lease_token,
                    succeeded=succeeded,
                    completed_at=completed_at,
                    failure_cooldown_seconds=(
                        failure_cooldown_seconds
                    ),
                    failure_kind=failure_kind,
                    error_code=error_code,
                    error_message=error_message,
                    metadata=metadata,
                )
            )



class DatabaseProviderHealthProbeCoordinator:
    """
    SQL-backed atomic health-recovery lease coordinator.

    The scoped health-state row is locked during admission. Only one process
    may hold an unexpired probe or recovering-request lease for a scope.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def try_claim_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        observed_at: datetime | None = None,
        lease_seconds: int = 60,
    ) -> ProviderHealthProbeClaim:
        now = _normalize_datetime(observed_at)

        try:
            normalized_user_id = UUID(str(user_id))
        except (TypeError, ValueError, AttributeError):
            return ProviderHealthProbeClaim(
                acquired=False,
                reason="invalid_user_scope",
                claimed_at=now,
            )

        if lease_seconds < 1:
            raise ValueError("probe lease_seconds must be >= 1")

        scope_key = build_provider_health_scope_key(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        result = await self.db.execute(
            select(CapabilityProviderHealthStateRecord)
            .where(CapabilityProviderHealthStateRecord.scope_key == scope_key)
            .with_for_update()
        )
        state = result.scalar_one_or_none()

        if state is None:
            claim = ProviderHealthProbeClaim(
                acquired=False,
                reason="health_state_not_found",
                scope_key=scope_key,
                claimed_at=now,
            )
            await self.db.rollback()
            return claim

        # Snapshot all ORM-backed values before commit/rollback. SQLAlchemy
        # expires instances when a transaction ends, and reading them after
        # rollback from ordinary Python code can trigger MissingGreenlet.
        current_state = state.current_state
        cooldown_until = state.cooldown_until
        manual_override_state = state.manual_override_state
        manual_override_until = state.manual_override_until
        existing_lease_token = state.probe_lease_token
        existing_lease_until = state.probe_lease_until

        override_active = bool(
            manual_override_state
            and (manual_override_until is None or manual_override_until > now)
        )

        if override_active:
            claim = ProviderHealthProbeClaim(
                acquired=False,
                reason="manual_override_active",
                scope_key=scope_key,
                claimed_at=now,
                current_state=current_state,
                manual_override_active=True,
                cooldown_until=cooldown_until,
            )
            await self.db.rollback()
            return claim

        if current_state not in {
            "unhealthy",
            "recovering",
        }:
            claim = ProviderHealthProbeClaim(
                acquired=False,
                reason="state_not_restricted",
                scope_key=scope_key,
                claimed_at=now,
                current_state=current_state,
                cooldown_until=cooldown_until,
            )
            await self.db.rollback()
            return claim

        if cooldown_until is not None and cooldown_until > now:
            claim = ProviderHealthProbeClaim(
                acquired=False,
                reason="cooldown_active",
                scope_key=scope_key,
                claimed_at=now,
                current_state=current_state,
                cooldown_until=cooldown_until,
            )
            await self.db.rollback()
            return claim

        if (
            existing_lease_token
            and existing_lease_until is not None
            and existing_lease_until > now
        ):
            claim = ProviderHealthProbeClaim(
                acquired=False,
                reason="probe_lease_active",
                scope_key=scope_key,
                claimed_at=now,
                current_state=current_state,
                lease_until=existing_lease_until,
                cooldown_until=cooldown_until,
            )
            await self.db.rollback()
            return claim

        token = uuid4().hex
        lease_until = now + timedelta(seconds=lease_seconds)

        state.probe_lease_token = token
        state.probe_lease_until = lease_until
        state.probe_claimed_at = now
        state.version = int(state.version or 0) + 1

        await self.db.commit()

        return ProviderHealthProbeClaim(
            acquired=True,
            reason=(
                "recovery_lease_acquired"
                if current_state == "recovering"
                else "probe_lease_acquired"
            ),
            scope_key=scope_key,
            lease_token=token,
            lease_until=lease_until,
            claimed_at=now,
            current_state=current_state,
            cooldown_until=cooldown_until,
        )

    async def complete_probe(
        self,
        *,
        user_id: str | None,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        lease_token: str,
        succeeded: bool,
        completed_at: datetime | None = None,
        failure_cooldown_seconds: int = 300,
        failure_kind: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderHealthProbeCompletion:
        now = _normalize_datetime(completed_at)
        normalized_token = str(lease_token or "").strip()

        if not normalized_token:
            raise ValueError("probe lease_token is required")

        if failure_cooldown_seconds < 0:
            raise ValueError("failure_cooldown_seconds must be >= 0")

        try:
            normalized_user_id = UUID(str(user_id))
        except (TypeError, ValueError, AttributeError):
            return ProviderHealthProbeCompletion(
                completed=False,
                reason="invalid_user_scope",
                lease_token=normalized_token,
                succeeded=succeeded,
                completed_at=now,
            )

        existing_result = await self.db.execute(
            select(CapabilityProviderHealthProbeResultRecord).where(
                CapabilityProviderHealthProbeResultRecord.lease_token
                == normalized_token
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            return ProviderHealthProbeCompletion(
                completed=True,
                duplicate=True,
                reason="probe_already_completed",
                scope_key=existing.scope_key,
                lease_token=normalized_token,
                succeeded=existing.succeeded,
                previous_state=existing.previous_state,
                resulting_state=existing.resulting_state,
                cooldown_until=existing.cooldown_until,
                completed_at=existing.completed_at,
                result_id=str(existing.id),
                state_version=None,
            )

        scope_key = build_provider_health_scope_key(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        state_result = await self.db.execute(
            select(CapabilityProviderHealthStateRecord)
            .where(CapabilityProviderHealthStateRecord.scope_key == scope_key)
            .with_for_update()
        )
        state = state_result.scalar_one_or_none()

        if state is None:
            await self.db.rollback()
            return ProviderHealthProbeCompletion(
                completed=False,
                reason="health_state_not_found",
                scope_key=scope_key,
                lease_token=normalized_token,
                succeeded=succeeded,
                completed_at=now,
            )

        # Another completion may have committed while this transaction waited
        # for the scoped health-state lock. Recheck history after acquiring
        # the lock so concurrent retries remain idempotent.
        duplicate_result = await self.db.execute(
            select(CapabilityProviderHealthProbeResultRecord).where(
                CapabilityProviderHealthProbeResultRecord.lease_token
                == normalized_token
            )
        )
        duplicate = duplicate_result.scalar_one_or_none()

        if duplicate is not None:
            # Snapshot ORM-backed fields before rollback. Transaction end
            # expires loaded instances, and later attribute access from normal
            # Python code can otherwise trigger MissingGreenlet.
            duplicate_scope_key = duplicate.scope_key
            duplicate_succeeded = duplicate.succeeded
            duplicate_previous_state = duplicate.previous_state
            duplicate_resulting_state = duplicate.resulting_state
            duplicate_cooldown_until = duplicate.cooldown_until
            duplicate_completed_at = duplicate.completed_at
            duplicate_id = str(duplicate.id)

            await self.db.rollback()

            return ProviderHealthProbeCompletion(
                completed=True,
                duplicate=True,
                reason="probe_already_completed",
                scope_key=duplicate_scope_key,
                lease_token=normalized_token,
                succeeded=duplicate_succeeded,
                previous_state=duplicate_previous_state,
                resulting_state=duplicate_resulting_state,
                cooldown_until=duplicate_cooldown_until,
                completed_at=duplicate_completed_at,
                result_id=duplicate_id,
                state_version=None,
            )

        active_token = state.probe_lease_token
        lease_until = state.probe_lease_until
        claimed_at = state.probe_claimed_at
        previous_state = state.current_state

        if active_token != normalized_token:
            await self.db.rollback()
            return ProviderHealthProbeCompletion(
                completed=False,
                reason="probe_lease_token_mismatch",
                scope_key=scope_key,
                lease_token=normalized_token,
                succeeded=succeeded,
                previous_state=previous_state,
                resulting_state=previous_state,
                completed_at=now,
            )

        if lease_until is not None and lease_until <= now:
            await self.db.rollback()
            return ProviderHealthProbeCompletion(
                completed=False,
                reason="probe_lease_expired",
                scope_key=scope_key,
                lease_token=normalized_token,
                succeeded=succeeded,
                previous_state=previous_state,
                resulting_state=previous_state,
                completed_at=now,
            )

        override_active = bool(
            state.manual_override_state
            and (
                state.manual_override_until is None or state.manual_override_until > now
            )
        )

        if override_active:
            resulting_state = previous_state
            reason = "manual_override_preserved"
            cooldown_until = state.cooldown_until
        elif succeeded:
            resulting_state = "recovering"
            reason = (
                "recovery_request_succeeded"
                if previous_state == "recovering"
                else "probe_succeeded"
            )
            cooldown_until = None
            state.current_state = resulting_state
            state.qualifying_recommendation = None
            state.qualifying_windows = 0
        else:
            resulting_state = "unhealthy"
            reason = (
                "recovery_request_failed"
                if previous_state == "recovering"
                else "probe_failed"
            )
            cooldown_until = (
                now + timedelta(seconds=failure_cooldown_seconds)
                if failure_cooldown_seconds > 0
                else now
            )
            state.current_state = resulting_state
            state.qualifying_recommendation = None
            state.qualifying_windows = 0

        state.cooldown_until = cooldown_until
        state.probe_lease_token = None
        state.probe_lease_until = None
        state.probe_claimed_at = None
        state.version = int(state.version or 0) + 1

        record = CapabilityProviderHealthProbeResultRecord(
            id=uuid4(),
            state_id=state.id,
            lease_token=normalized_token,
            scope_key=scope_key,
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
            succeeded=bool(succeeded),
            previous_state=previous_state,
            resulting_state=resulting_state,
            failure_kind=failure_kind,
            error_code=error_code,
            error_message=error_message,
            claimed_at=claimed_at,
            lease_until=lease_until,
            completed_at=now,
            cooldown_until=cooldown_until,
            metadata_json=metadata or {},
        )
        self.db.add(record)

        await self.db.commit()

        return ProviderHealthProbeCompletion(
            completed=True,
            duplicate=False,
            reason=reason,
            scope_key=scope_key,
            lease_token=normalized_token,
            succeeded=bool(succeeded),
            previous_state=previous_state,
            resulting_state=resulting_state,
            cooldown_until=cooldown_until,
            completed_at=now,
            result_id=str(record.id),
            state_version=state.version,
        )


def _normalize_datetime(
    value: datetime | None,
) -> datetime:
    result = value or datetime.now(timezone.utc)

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result.astimezone(timezone.utc)


__all__ = [
    "DatabaseProviderHealthProbeCoordinator",
    "IsolatedDatabaseProviderHealthProbeCoordinator",
    "NullProviderHealthProbeCoordinator",
    "ProviderHealthProbeClaim",
    "ProviderHealthProbeCompletion",
    "ProviderHealthProbeCoordinator",
]
