from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthDecisionAction,
    ProviderHealthDecisionReason,
    ProviderHealthDecisionScope,
    ProviderHealthState,
    ProposedProviderHealthDecision,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)
from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityReliabilityRecommendation,
)


NOW = datetime(
    2026,
    7,
    12,
    12,
    0,
    tzinfo=timezone.utc,
)


def decision(
    *,
    user_id,
    tenant_id="tenant_1",
    current_state=ProviderHealthState.HEALTHY,
    proposed_state=ProviderHealthState.DEGRADED,
    action=(
        ProviderHealthDecisionAction
        .PROPOSE_TRANSITION
    ),
    reason=(
        ProviderHealthDecisionReason
        .DEGRADATION_CONFIRMED
    ),
    evaluated_at=NOW,
):
    return ProposedProviderHealthDecision(
        scope=ProviderHealthDecisionScope(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        ),
        current_state=current_state,
        proposed_state=proposed_state,
        action=action,
        reason=reason,
        evidence_recommendation=(
            CapabilityReliabilityRecommendation
            .DEGRADED
        ),
        evidence_sufficient=True,
        attempts=20,
        successes=19,
        failures=1,
        success_rate=0.95,
        qualifying_windows=2,
        required_windows=2,
        window_start=evaluated_at - timedelta(hours=1),
        window_end=evaluated_at,
        cooldown_until=None,
        evaluated_at=evaluated_at,
        explanation="confirmed degradation",
    )


@pytest.mark.asyncio
async def test_persisted_transition_updates_only_scoped_state():
    first_user = uuid4()
    second_user = uuid4()

    async with SessionLocal() as db:
        repo = CapabilityProviderHealthRepository(db)

        first_state, first_record, inserted = (
            await repo.persist_decision(
                decision=decision(
                    user_id=first_user,
                )
            )
        )

        second_state, _, _ = (
            await repo.persist_decision(
                decision=decision(
                    user_id=second_user,
                )
            )
        )

    assert inserted is True
    assert first_state.current_state == "degraded"
    assert first_record.previous_state == "healthy"
    assert first_record.resulting_state == "degraded"
    assert first_state.id != second_state.id
    assert first_state.scope_key != second_state.scope_key


@pytest.mark.asyncio
async def test_duplicate_decision_is_idempotent():
    user_id = uuid4()
    item = decision(user_id=user_id)

    async with SessionLocal() as db:
        repo = CapabilityProviderHealthRepository(db)

        first_state, first_record, first_inserted = (
            await repo.persist_decision(
                decision=item
            )
        )

        (
            second_state,
            second_record,
            second_inserted,
        ) = await repo.persist_decision(
            decision=item
        )

        history = await repo.list_decisions(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
        )

    assert first_inserted is True
    assert second_inserted is False
    assert first_record.id == second_record.id
    assert first_state.id == second_state.id
    assert first_state.version == second_state.version
    assert len(history) == 1


@pytest.mark.asyncio
async def test_hold_decision_preserves_current_state():
    user_id = uuid4()

    held = decision(
        user_id=user_id,
        current_state=ProviderHealthState.HEALTHY,
        proposed_state=ProviderHealthState.HEALTHY,
        action=ProviderHealthDecisionAction.HOLD,
        reason=ProviderHealthDecisionReason.STABLE,
    )

    async with SessionLocal() as db:
        state, record, inserted = (
            await CapabilityProviderHealthRepository(
                db
            ).persist_decision(
                decision=held
            )
        )

    assert inserted is True
    assert state.current_state == "healthy"
    assert record.previous_state == "healthy"
    assert record.resulting_state == "healthy"


@pytest.mark.asyncio
async def test_decision_history_is_scoped_by_user():
    first_user = uuid4()
    second_user = uuid4()

    async with SessionLocal() as db:
        repo = CapabilityProviderHealthRepository(db)

        await repo.persist_decision(
            decision=decision(
                user_id=first_user,
            )
        )
        await repo.persist_decision(
            decision=decision(
                user_id=second_user,
            )
        )

        first_history = await repo.list_decisions(
            user_id=first_user,
        )

    assert len(first_history) == 1
    assert first_history[0].user_id == first_user


@pytest.mark.asyncio
async def test_manual_override_reserved_state_wins_over_decision():
    user_id = uuid4()

    async with SessionLocal() as db:
        repo = CapabilityProviderHealthRepository(db)

        state, _, _ = await repo.persist_decision(
            decision=decision(
                user_id=user_id,
            )
        )

        state.manual_override_state = "healthy"
        state.manual_override_reason = "operator override"
        await db.commit()

        next_item = decision(
            user_id=user_id,
            current_state=ProviderHealthState.DEGRADED,
            proposed_state=ProviderHealthState.UNHEALTHY,
            reason=(
                ProviderHealthDecisionReason
                .UNHEALTHY_CONFIRMED
            ),
            evaluated_at=NOW + timedelta(hours=1),
        )

        updated_state, record, _ = (
            await repo.persist_decision(
                decision=next_item
            )
        )

    # Evidence-derived state continues progressing under the override,
    # while resulting/effective state remains operator-controlled.
    assert updated_state.current_state == "unhealthy"
    assert updated_state.manual_override_state == "healthy"
    assert record.proposed_state == "unhealthy"
    assert record.resulting_state == "healthy"
