from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    CapabilityProviderHealthDecisionRecord,
    CapabilityProviderHealthStateRecord,
)
from app.runtime.capabilities.execution.health.decisions import (
    ProposedProviderHealthDecision,
    ProviderHealthDecisionAction,
    ProviderHealthState,
)


def normalize_user_id(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(
            "user_id must be a valid UUID"
        ) from exc


def build_provider_health_scope_key(
    *,
    user_id: Any,
    tenant_id: str | None,
    capability_id: str,
    provider_id: str,
    provider_ref: str | None,
) -> str:
    normalized_user_id = normalize_user_id(user_id)

    parts = (
        str(normalized_user_id),
        str(tenant_id or ""),
        str(capability_id or "").strip(),
        str(provider_id or "").strip(),
        str(provider_ref or ""),
    )

    if not parts[2]:
        raise ValueError("capability_id cannot be empty")
    if not parts[3]:
        raise ValueError("provider_id cannot be empty")

    return "|".join(parts)


def build_provider_health_evaluation_key(
    *,
    scope_key: str,
    window_start: datetime,
    window_end: datetime,
) -> str:
    """
    Identify one exact evaluation window independently of its outcome.

    Unlike decision_key, this identity does not contain state, action, reason,
    or qualifying-window values. Concurrent retries therefore compete for the
    same database identity.
    """

    raw = "|".join(
        (
            scope_key,
            window_start.isoformat(),
            window_end.isoformat(),
        )
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def build_provider_health_decision_key(
    *,
    scope_key: str,
    decision: ProposedProviderHealthDecision,
) -> str:
    raw = "|".join(
        (
            scope_key,
            decision.window_start.isoformat(),
            decision.window_end.isoformat(),
            decision.evaluated_at.isoformat(),
            decision.current_state.value,
            decision.proposed_state.value,
            decision.action.value,
            decision.reason.value,
        )
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


class CapabilityProviderHealthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_state(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
    ) -> CapabilityProviderHealthStateRecord | None:
        scope_key = build_provider_health_scope_key(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        result = await self.db.execute(
            select(CapabilityProviderHealthStateRecord)
            .where(
                CapabilityProviderHealthStateRecord.scope_key
                == scope_key
            )
        )
        return result.scalar_one_or_none()

    async def list_states(
        self,
        *,
        user_id: Any,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CapabilityProviderHealthStateRecord]:
        normalized_user_id = normalize_user_id(
            user_id
        )

        stmt = (
            select(CapabilityProviderHealthStateRecord)
            .where(
                CapabilityProviderHealthStateRecord.user_id
                == normalized_user_id
            )
            .order_by(
                CapabilityProviderHealthStateRecord
                .updated_at
                .desc(),
                CapabilityProviderHealthStateRecord
                .id
                .desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        if tenant_id is not None:
            stmt = stmt.where(
                CapabilityProviderHealthStateRecord.tenant_id
                == tenant_id
            )

        if capability_id is not None:
            stmt = stmt.where(
                CapabilityProviderHealthStateRecord.capability_id
                == capability_id
            )

        if provider_id is not None:
            stmt = stmt.where(
                CapabilityProviderHealthStateRecord.provider_id
                == provider_id
            )

        if provider_ref is not None:
            stmt = stmt.where(
                CapabilityProviderHealthStateRecord.provider_ref
                == provider_ref
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def set_manual_override(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        override_state: ProviderHealthState,
        reason: str,
        override_until: datetime | None,
    ) -> CapabilityProviderHealthStateRecord:
        normalized_user_id = normalize_user_id(
            user_id
        )
        scope_key = build_provider_health_scope_key(
            user_id=normalized_user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        await self.db.execute(
            insert(CapabilityProviderHealthStateRecord)
            .values(
                id=uuid4(),
                scope_key=scope_key,
                user_id=normalized_user_id,
                tenant_id=tenant_id,
                capability_id=capability_id,
                provider_id=provider_id,
                provider_ref=provider_ref,
                current_state=ProviderHealthState.HEALTHY.value,
                qualifying_recommendation=None,
                qualifying_windows=0,
                version=1,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    CapabilityProviderHealthStateRecord
                    .scope_key
                ]
            )
        )

        result = await self.db.execute(
            select(CapabilityProviderHealthStateRecord)
            .where(
                CapabilityProviderHealthStateRecord.scope_key
                == scope_key
            )
            .with_for_update()
        )
        state = result.scalar_one()

        state.manual_override_state = (
            override_state.value
        )
        state.manual_override_reason = reason
        state.manual_override_until = override_until
        state.version = int(state.version or 0) + 1

        await self.db.commit()
        await self.db.refresh(state)
        return state

    async def clear_manual_override(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
    ) -> CapabilityProviderHealthStateRecord | None:
        scope_key = build_provider_health_scope_key(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )

        result = await self.db.execute(
            select(CapabilityProviderHealthStateRecord)
            .where(
                CapabilityProviderHealthStateRecord.scope_key
                == scope_key
            )
            .with_for_update()
        )
        state = result.scalar_one_or_none()

        if state is None:
            await self.db.rollback()
            return None

        state.manual_override_state = None
        state.manual_override_reason = None
        state.manual_override_until = None
        state.version = int(state.version or 0) + 1

        await self.db.commit()
        await self.db.refresh(state)
        return state

    async def get_decision_for_window(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
        window_start: datetime,
        window_end: datetime,
    ) -> CapabilityProviderHealthDecisionRecord | None:
        scope_key = build_provider_health_scope_key(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id=capability_id,
            provider_id=provider_id,
            provider_ref=provider_ref,
        )
        evaluation_key = (
            build_provider_health_evaluation_key(
                scope_key=scope_key,
                window_start=window_start,
                window_end=window_end,
            )
        )

        result = await self.db.execute(
            select(CapabilityProviderHealthDecisionRecord)
            .where(
                CapabilityProviderHealthDecisionRecord
                .evaluation_key
                == evaluation_key
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_decision(
        self,
        *,
        user_id: Any,
        tenant_id: str | None,
        capability_id: str,
        provider_id: str,
        provider_ref: str | None,
    ) -> CapabilityProviderHealthDecisionRecord | None:
        normalized_user_id = normalize_user_id(
            user_id
        )

        result = await self.db.execute(
            select(CapabilityProviderHealthDecisionRecord)
            .where(
                CapabilityProviderHealthDecisionRecord.user_id
                == normalized_user_id,
                CapabilityProviderHealthDecisionRecord.tenant_id
                == tenant_id,
                CapabilityProviderHealthDecisionRecord.capability_id
                == capability_id,
                CapabilityProviderHealthDecisionRecord.provider_id
                == provider_id,
                CapabilityProviderHealthDecisionRecord.provider_ref
                == provider_ref,
            )
            .order_by(
                CapabilityProviderHealthDecisionRecord
                .window_end
                .desc(),
                CapabilityProviderHealthDecisionRecord
                .created_at
                .desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def persist_decision(
        self,
        *,
        decision: ProposedProviderHealthDecision,
    ) -> tuple[
        CapabilityProviderHealthStateRecord,
        CapabilityProviderHealthDecisionRecord,
        bool,
    ]:
        user_id = normalize_user_id(
            decision.scope.user_id
        )

        scope_key = build_provider_health_scope_key(
            user_id=user_id,
            tenant_id=decision.scope.tenant_id,
            capability_id=decision.scope.capability_id,
            provider_id=decision.scope.provider_id,
            provider_ref=decision.scope.provider_ref,
        )

        decision_key = build_provider_health_decision_key(
            scope_key=scope_key,
            decision=decision,
        )

        evaluation_key = (
            build_provider_health_evaluation_key(
                scope_key=scope_key,
                window_start=decision.window_start,
                window_end=decision.window_end,
            )
        )

        existing_result = await self.db.execute(
            select(CapabilityProviderHealthDecisionRecord)
            .where(
                CapabilityProviderHealthDecisionRecord
                .evaluation_key
                == evaluation_key
            )
        )
        existing_decision = (
            existing_result.scalar_one_or_none()
        )

        if existing_decision is not None:
            state_result = await self.db.execute(
                select(CapabilityProviderHealthStateRecord)
                .where(
                    CapabilityProviderHealthStateRecord.id
                    == existing_decision.state_id
                )
            )
            state = state_result.scalar_one()
            return state, existing_decision, False

        await self.db.execute(
            insert(CapabilityProviderHealthStateRecord)
            .values(
                id=uuid4(),
                scope_key=scope_key,
                user_id=user_id,
                tenant_id=decision.scope.tenant_id,
                capability_id=(
                    decision.scope.capability_id
                ),
                provider_id=decision.scope.provider_id,
                provider_ref=decision.scope.provider_ref,
                current_state=(
                    decision.current_state.value
                ),
                qualifying_recommendation=None,
                qualifying_windows=0,
                version=1,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    CapabilityProviderHealthStateRecord
                    .scope_key
                ]
            )
        )

        state_result = await self.db.execute(
            select(CapabilityProviderHealthStateRecord)
            .where(
                CapabilityProviderHealthStateRecord.scope_key
                == scope_key
            )
            .with_for_update()
        )
        state = state_result.scalar_one()

        duplicate_result = await self.db.execute(
            select(CapabilityProviderHealthDecisionRecord)
            .where(
                CapabilityProviderHealthDecisionRecord
                .evaluation_key
                == evaluation_key
            )
        )
        duplicate = duplicate_result.scalar_one_or_none()

        if duplicate is not None:
            await self.db.commit()
            await self.db.refresh(state)
            return state, duplicate, False

        previous_state = ProviderHealthState(
            state.current_state
        )

        if (
            decision.action
            == ProviderHealthDecisionAction
            .PROPOSE_TRANSITION
        ):
            underlying_state = decision.proposed_state
        else:
            underlying_state = previous_state

        override_active = bool(
            state.manual_override_state
            and (
                state.manual_override_until is None
                or state.manual_override_until
                > decision.evaluated_at
            )
        )

        if (
            state.manual_override_state
            and not override_active
        ):
            state.manual_override_state = None
            state.manual_override_reason = None
            state.manual_override_until = None

        if override_active:
            resulting_state = ProviderHealthState(
                state.manual_override_state
            )
        else:
            resulting_state = underlying_state

        if not decision.evidence_sufficient:
            state.qualifying_recommendation = None
            state.qualifying_windows = 0
        elif (
            state.qualifying_recommendation
            == decision.evidence_recommendation.value
        ):
            state.qualifying_windows = max(
                int(state.qualifying_windows or 0),
                decision.qualifying_windows,
            )
        else:
            state.qualifying_recommendation = (
                decision.evidence_recommendation.value
            )
            state.qualifying_windows = (
                decision.qualifying_windows
            )

        # current_state remains the evidence-derived state.
        # Manual override is an effective-state overlay only.
        state.current_state = underlying_state.value
        state.cooldown_until = decision.cooldown_until
        state.last_evaluated_at = (
            decision.evaluated_at
        )
        state.version = int(state.version or 0) + 1

        record = CapabilityProviderHealthDecisionRecord(
            id=uuid4(),
            state_id=state.id,
            decision_key=decision_key,
            evaluation_key=evaluation_key,
            user_id=user_id,
            tenant_id=decision.scope.tenant_id,
            capability_id=(
                decision.scope.capability_id
            ),
            provider_id=decision.scope.provider_id,
            provider_ref=decision.scope.provider_ref,
            previous_state=previous_state.value,
            proposed_state=decision.proposed_state.value,
            resulting_state=resulting_state.value,
            action=decision.action.value,
            reason=decision.reason.value,
            evidence_recommendation=(
                decision.evidence_recommendation.value
            ),
            evidence_sufficient=(
                decision.evidence_sufficient
            ),
            qualifying_windows=(
                decision.qualifying_windows
            ),
            required_windows=decision.required_windows,
            window_start=decision.window_start,
            window_end=decision.window_end,
            evaluated_at=decision.evaluated_at,
            cooldown_until=decision.cooldown_until,
            evidence_json=decision.model_dump(
                mode="json"
            ),
            explanation=decision.explanation,
            state_version=state.version,
        )

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(state)
        await self.db.refresh(record)

        return state, record, True

    async def list_decisions(
        self,
        *,
        user_id: Any,
        tenant_id: str | None = None,
        capability_id: str | None = None,
        provider_id: str | None = None,
        provider_ref: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CapabilityProviderHealthDecisionRecord]:
        normalized_user_id = normalize_user_id(
            user_id
        )

        stmt = (
            select(CapabilityProviderHealthDecisionRecord)
            .where(
                CapabilityProviderHealthDecisionRecord.user_id
                == normalized_user_id
            )
            .order_by(
                CapabilityProviderHealthDecisionRecord
                .evaluated_at
                .desc()
            )
            .limit(limit)
            .offset(offset)
        )

        if tenant_id is not None:
            stmt = stmt.where(
                CapabilityProviderHealthDecisionRecord.tenant_id
                == tenant_id
            )

        if capability_id is not None:
            stmt = stmt.where(
                CapabilityProviderHealthDecisionRecord
                .capability_id
                == capability_id
            )

        if provider_id is not None:
            stmt = stmt.where(
                CapabilityProviderHealthDecisionRecord
                .provider_id
                == provider_id
            )

        if provider_ref is not None:
            stmt = stmt.where(
                CapabilityProviderHealthDecisionRecord
                .provider_ref
                == provider_ref
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


__all__ = [
    "CapabilityProviderHealthRepository",
    "build_provider_health_decision_key",
    "build_provider_health_evaluation_key",
    "build_provider_health_scope_key",
    "normalize_user_id",
]
