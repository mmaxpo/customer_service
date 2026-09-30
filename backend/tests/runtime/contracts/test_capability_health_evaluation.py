from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.events.event_store import PlatformEventStore
from app.runtime.capabilities.execution.health.evaluation import (
    CapabilityHealthEvaluationRequest,
    CapabilityHealthEvaluationService,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)
from app.runtime.capabilities.execution.health.reader import (
    DatabaseProviderHealthReader,
)
from app.runtime.capabilities.execution.health.probes import (
    DatabaseProviderHealthProbeCoordinator,
)
from app.runtime.capabilities.execution.health.decisions import (
    ProviderHealthState,
)
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceObservation,
    CapabilityPerformanceObservationStatus,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)


WINDOW_END = datetime(
    2026,
    7,
    12,
    18,
    0,
    tzinfo=timezone.utc,
)


async def record_window(
    *,
    db,
    user_id,
    successes,
    failures,
    tenant_id="tenant_1",
    window_end=WINDOW_END,
):
    observations = []
    total = successes + failures

    for index in range(total):
        succeeded = index < successes
        correlation_id = f"health-eval-{uuid4()}"

        event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=(
                "runtime.capability.execution.completed"
            ),
            source="runtime.capabilities",
            payload={},
            meta={"correlation_id": correlation_id},
        )

        observations = [
            CapabilityPerformanceObservation(
                correlation_id=correlation_id,
                attempt_index=0,
                requested_capability_id=(
                    "shopify.get_order"
                ),
                resolved_capability_id=(
                    "ecommerce.orders.get"
                ),
                provider_id="shopify",
                provider_ref="shopify.get_order",
                status=(
                    CapabilityPerformanceObservationStatus
                    .SUCCEEDED
                    if succeeded
                    else CapabilityPerformanceObservationStatus
                    .FAILED
                ),
                succeeded=succeeded,
                duration_ms=10.0,
                failure_kind=(
                    None if succeeded else "timeout"
                ),
                tenant_id=tenant_id,
                observed_at_ts=(
                    window_end
                    - timedelta(minutes=index + 1)
                ).timestamp(),
            )
        ]

        await CapabilityPerformanceObservationRepository(
            db
        ).record_many(
            source_event_id=event.id,
            observations=observations,
        )


def request(*, user_id, window_end=WINDOW_END):
    return CapabilityHealthEvaluationRequest(
        user_id=user_id,
        tenant_id="tenant_1",
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.get_order",
        window_hours=1,
        window_end=window_end,
        minimum_attempts=10,
        degrade_after_windows=2,
        unhealthy_after_windows=3,
        recover_after_windows=2,
        cooldown_seconds=300,
    )


@pytest.mark.asyncio
async def test_evaluation_persists_first_degraded_window_as_hold():
    user_id = uuid4()

    async with SessionLocal() as db:
        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
        )

        result = await CapabilityHealthEvaluationService(
            db
        ).evaluate(
            request=request(user_id=user_id)
        )

        state = await CapabilityProviderHealthRepository(
            db
        ).get_state(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert result["status"] == "evaluated"
    assert result["recommendation"] == "degraded"
    assert result["qualifying_windows"] == 1
    assert result["decision"]["action"] == "hold"
    assert state is not None
    assert state.current_state == "healthy"
    assert state.qualifying_windows == 1


@pytest.mark.asyncio
async def test_second_degraded_window_proposes_transition():
    user_id = uuid4()

    async with SessionLocal() as db:
        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
        )

        service = CapabilityHealthEvaluationService(db)

        first = await service.evaluate(
            request=request(user_id=user_id)
        )

        second_window_end = (
            WINDOW_END + timedelta(hours=1)
        )

        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
            window_end=second_window_end,
        )

        second = await service.evaluate(
            request=request(
                user_id=user_id,
                window_end=second_window_end,
            )
        )

        state = await CapabilityProviderHealthRepository(
            db
        ).get_state(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert first["qualifying_windows"] == 1
    assert second["qualifying_windows"] == 2
    assert second["decision"]["action"] == (
        "propose_transition"
    )
    assert second["decision"]["proposed_state"] == (
        "degraded"
    )
    assert state is not None
    assert state.current_state == "degraded"


@pytest.mark.asyncio
async def test_same_window_retry_is_idempotent():
    user_id = uuid4()

    async with SessionLocal() as db:
        await record_window(
            db=db,
            user_id=user_id,
            successes=19,
            failures=1,
        )

        service = CapabilityHealthEvaluationService(db)
        item = request(user_id=user_id)

        first = await service.evaluate(request=item)
        second = await service.evaluate(request=item)

        history = await CapabilityProviderHealthRepository(
            db
        ).list_decisions(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
        )

    assert first["persistence"]["inserted"] is True
    assert second["persistence"]["inserted"] is False
    assert (
        first["persistence"]["decision_id"]
        == second["persistence"]["decision_id"]
    )
    assert len(history) == 1


@pytest.mark.asyncio
async def test_no_evidence_does_not_create_state():
    user_id = uuid4()

    async with SessionLocal() as db:
        result = await CapabilityHealthEvaluationService(
            db
        ).evaluate(
            request=request(user_id=user_id)
        )

        state = await CapabilityProviderHealthRepository(
            db
        ).get_state(
            user_id=user_id,
            tenant_id="tenant_1",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

    assert result["status"] == "no_evidence"
    assert result["persisted"] is False
    assert state is None


@pytest.mark.asyncio
async def test_recovering_provider_is_promoted_after_two_healthy_windows():
    user_id = uuid4()
    tenant_id = "tenant_recovery_promotion"
    first_window_end = WINDOW_END
    second_window_end = (
        first_window_end + timedelta(hours=1)
    )

    async with SessionLocal() as db:
        repo = CapabilityProviderHealthRepository(db)

        # Create the durable scope, then model the state produced by a
        # successful controlled probe/recovery request.
        state = await repo.set_manual_override(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            override_state=ProviderHealthState.HEALTHY,
            reason="create recovery promotion scope",
            override_until=(
                first_window_end - timedelta(seconds=1)
            ),
        )

        state.current_state = (
            ProviderHealthState.RECOVERING.value
        )
        state.manual_override_state = None
        state.manual_override_reason = None
        state.manual_override_until = None
        state.cooldown_until = None
        state.qualifying_recommendation = None
        state.qualifying_windows = 0
        state.probe_lease_token = None
        state.probe_lease_until = None
        state.probe_claimed_at = None
        await db.commit()

        # Ten successful observations make the first completed hour a
        # sufficient healthy window.
        await record_window(
            db=db,
            user_id=user_id,
            successes=10,
            failures=0,
            tenant_id=tenant_id,
            window_end=first_window_end,
        )

        first = await CapabilityHealthEvaluationService(
            db
        ).evaluate(
            request=CapabilityHealthEvaluationRequest(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
                window_hours=1,
                window_end=first_window_end,
                minimum_attempts=10,
                degrade_after_windows=2,
                unhealthy_after_windows=3,
                recover_after_windows=2,
                cooldown_seconds=300,
            )
        )

        after_first = await repo.get_state(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

        assert first["status"] == "evaluated"
        assert first["recommendation"] == "healthy"
        assert first["qualifying_windows"] == 1
        assert (
            first["decision"]["reason"]
            == "recovery_pending"
        )
        assert (
            first["decision"]["action"]
            == "hold"
        )
        assert after_first is not None
        assert (
            after_first.current_state
            == ProviderHealthState.RECOVERING.value
        )
        assert after_first.qualifying_windows == 1

        # The next completed hour is adjacent and independently contains
        # sufficient healthy evidence.
        await record_window(
            db=db,
            user_id=user_id,
            successes=10,
            failures=0,
            tenant_id=tenant_id,
            window_end=second_window_end,
        )

        second = await CapabilityHealthEvaluationService(
            db
        ).evaluate(
            request=CapabilityHealthEvaluationRequest(
                user_id=user_id,
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
                window_hours=1,
                window_end=second_window_end,
                minimum_attempts=10,
                degrade_after_windows=2,
                unhealthy_after_windows=3,
                recover_after_windows=2,
                cooldown_seconds=300,
            )
        )

        promoted = await repo.get_state(
            user_id=user_id,
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
        )

        assert second["status"] == "evaluated"
        assert second["recommendation"] == "healthy"
        assert second["qualifying_windows"] == 2
        assert (
            second["decision"]["reason"]
            == "recovery_confirmed"
        )
        assert (
            second["decision"]["action"]
            == "propose_transition"
        )
        assert (
            second["decision"]["proposed_state"]
            == "healthy"
        )

        assert promoted is not None
        assert (
            promoted.current_state
            == ProviderHealthState.HEALTHY.value
        )
        assert promoted.qualifying_windows == 2

        snapshot = await DatabaseProviderHealthReader(
            db
        ).get_effective_health(
            user_id=str(user_id),
            tenant_id=tenant_id,
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            observed_at=(
                second_window_end
                + timedelta(seconds=1)
            ),
        )

        assert snapshot.found is True
        assert snapshot.current_state == "healthy"
        assert snapshot.effective_state == "healthy"

        # Healthy providers no longer consume a controlled recovery lease.
        claim = await (
            DatabaseProviderHealthProbeCoordinator(
                db
            ).try_claim_probe(
                user_id=str(user_id),
                tenant_id=tenant_id,
                capability_id="ecommerce.orders.get",
                provider_id="shopify",
                provider_ref="shopify.get_order",
                observed_at=(
                    second_window_end
                    + timedelta(seconds=1)
                ),
            )
        )

    assert claim.acquired is False
    assert claim.reason == "state_not_restricted"
    assert claim.current_state == "healthy"
