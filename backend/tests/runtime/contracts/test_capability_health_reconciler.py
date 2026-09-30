from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.models.models import PlatformJob
from app.platform.composition import build_default_job_registry
from app.platform.events.event_store import PlatformEventStore
from app.runtime.capabilities.execution.health.reconciler import (
    CapabilityHealthEvaluationReconciler,
    CapabilityHealthReconcileRequest,
)
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceObservation,
    CapabilityPerformanceObservationStatus,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)


async def record_observation(
    *,
    db,
    user_id,
    observed_at,
    tenant_id="tenant_reconcile",
):
    correlation_id = f"reconcile-{uuid4()}"

    event = await PlatformEventStore(db).append(
        user_id=user_id,
        event_type=("runtime.capability.execution.completed"),
        source="runtime.capabilities",
        payload={},
        meta={"correlation_id": correlation_id},
    )

    await CapabilityPerformanceObservationRepository(db).record_many(
        source_event_id=event.id,
        observations=[
            CapabilityPerformanceObservation(
                correlation_id=correlation_id,
                attempt_index=0,
                requested_capability_id=("shopify.get_order"),
                resolved_capability_id=("ecommerce.orders.get"),
                provider_id="shopify",
                provider_ref="shopify.get_order",
                status=(CapabilityPerformanceObservationStatus.SUCCEEDED),
                succeeded=True,
                duration_ms=10.0,
                tenant_id=tenant_id,
                observed_at_ts=(observed_at.timestamp()),
            )
        ],
    )


@pytest.mark.asyncio
async def test_reconciler_enqueues_completed_window_once():
    user_id = uuid4()
    now = datetime(
        2026,
        7,
        13,
        18,
        25,
        tzinfo=timezone.utc,
    )
    completed_end = datetime(
        2026,
        7,
        13,
        18,
        0,
        tzinfo=timezone.utc,
    )

    async with SessionLocal() as db:
        await record_observation(
            db=db,
            user_id=user_id,
            observed_at=(completed_end - timedelta(minutes=10)),
        )

        reconciler = CapabilityHealthEvaluationReconciler(db)
        request = CapabilityHealthReconcileRequest(
            now=now,
            window_hours=1,
            lookback_windows=1,
        )

        first = await reconciler.reconcile(request=request)
        second = await reconciler.reconcile(request=request)

        decision = await CapabilityProviderHealthRepository(db).get_decision_for_window(
            user_id=user_id,
            tenant_id="tenant_reconcile",
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            provider_ref="shopify.get_order",
            window_start=(completed_end - timedelta(hours=1)),
            window_end=completed_end,
        )

        count = await db.scalar(
            select(func.count(PlatformJob.id)).where(
                PlatformJob.job_type == "capability.health.evaluate",
                PlatformJob.user_id == user_id,
            )
        )

    first_matching = [
        item
        for item in first["jobs"]
        if item["user_id"] == str(user_id) and item["tenant_id"] == "tenant_reconcile"
    ]
    second_matching = [
        item
        for item in second["jobs"]
        if item["user_id"] == str(user_id) and item["tenant_id"] == "tenant_reconcile"
    ]

    assert len(first_matching) == 1
    assert first_matching[0]["inserted"] is True

    assert count == 1

    if second_matching:
        # The worker has not consumed the job yet. Reconciliation
        # returns the same durable job without inserting another.
        assert len(second_matching) == 1
        assert second_matching[0]["inserted"] is False
        assert first_matching[0]["job_id"] == second_matching[0]["job_id"]
        assert (
            first_matching[0]["evaluation_key"] == second_matching[0]["evaluation_key"]
        )
    else:
        # A live worker may consume the job between reconciliations.
        # Then the exact durable health decision is the idempotent
        # terminal state for this evaluation window.
        assert decision is not None
        assert decision.evaluation_key == first_matching[0]["evaluation_key"]


@pytest.mark.asyncio
async def test_reconciler_ignores_open_window():
    user_id = uuid4()
    now = datetime(
        2026,
        7,
        13,
        18,
        25,
        tzinfo=timezone.utc,
    )

    async with SessionLocal() as db:
        await record_observation(
            db=db,
            user_id=user_id,
            observed_at=(now - timedelta(minutes=5)),
            tenant_id="tenant_open_window",
        )

        result = await (CapabilityHealthEvaluationReconciler(db)).reconcile(
            request=CapabilityHealthReconcileRequest(
                now=now,
                window_hours=1,
                lookback_windows=1,
            )
        )

        count = await db.scalar(
            select(func.count(PlatformJob.id)).where(
                PlatformJob.job_type == "capability.health.evaluate",
                PlatformJob.user_id == user_id,
            )
        )

    assert result["jobs_enqueued"] == 0
    assert count == 0


@pytest.mark.asyncio
async def test_reconciler_catches_up_bounded_windows():
    user_id = uuid4()
    now = datetime(
        2026,
        7,
        13,
        18,
        25,
        tzinfo=timezone.utc,
    )

    async with SessionLocal() as db:
        for hour in (16, 17):
            await record_observation(
                db=db,
                user_id=user_id,
                observed_at=datetime(
                    2026,
                    7,
                    13,
                    hour,
                    30,
                    tzinfo=timezone.utc,
                ),
                tenant_id="tenant_catchup",
            )

        result = await (CapabilityHealthEvaluationReconciler(db)).reconcile(
            request=CapabilityHealthReconcileRequest(
                now=now,
                window_hours=1,
                lookback_windows=2,
            )
        )

    assert result["windows_scanned"] == 2
    assert result["jobs_enqueued"] == 2


def test_health_reconcile_handler_is_registered():

    assert build_default_job_registry().get("capability.health.reconcile") is not None
