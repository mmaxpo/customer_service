from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.events.event_store import PlatformEventStore
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceObservation,
    CapabilityPerformanceObservationStatus,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)
from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityReliabilityPolicy,
    CapabilityReliabilityRecommendation,
)
from app.runtime.capabilities.execution.performance.reliability_service import (
    CapabilityReliabilityService,
)


async def record_observations(
    *,
    db,
    user_id,
    correlation_id,
    observations,
):
    event = await PlatformEventStore(db).append(
        user_id=user_id,
        event_type="runtime.capability.execution.completed",
        source="runtime.capabilities",
        payload={},
        meta={"correlation_id": correlation_id},
    )

    inserted = await CapabilityPerformanceObservationRepository(
        db
    ).record_many(
        source_event_id=event.id,
        observations=observations,
    )

    assert inserted == len(observations)


def observation(
    *,
    correlation_id,
    attempt_index,
    succeeded,
    provider_id="shopify",
    failure_kind=None,
    fallback_allowed=False,
    fallback_used=False,
    final_attempt=True,
):
    return CapabilityPerformanceObservation(
        correlation_id=correlation_id,
        attempt_index=attempt_index,
        requested_capability_id="shopify.get_order",
        resolved_capability_id="ecommerce.orders.get",
        provider_id=provider_id,
        provider_ref=f"{provider_id}.get_order",
        status=(
            CapabilityPerformanceObservationStatus.SUCCEEDED
            if succeeded
            else CapabilityPerformanceObservationStatus.FAILED
        ),
        succeeded=succeeded,
        duration_ms=10.0,
        failure_kind=failure_kind,
        fallback_allowed=fallback_allowed,
        fallback_used=fallback_used,
        final_attempt=final_attempt,
        tenant_id="tenant_1",
        observed_at_ts=datetime.now(
            timezone.utc
        ).timestamp(),
    )


@pytest.mark.asyncio
async def test_reliability_summary_is_scoped_to_authenticated_user():
    first_user = uuid4()
    second_user = uuid4()

    async with SessionLocal() as db:
        for index in range(10):
            correlation_id = f"first-{uuid4()}"

            await record_observations(
                db=db,
                user_id=first_user,
                correlation_id=correlation_id,
                observations=[
                    observation(
                        correlation_id=correlation_id,
                        attempt_index=0,
                        succeeded=(index != 0),
                        failure_kind=(
                            "timeout"
                            if index == 0
                            else None
                        ),
                    )
                ],
            )

        for _ in range(4):
            correlation_id = f"second-{uuid4()}"

            await record_observations(
                db=db,
                user_id=second_user,
                correlation_id=correlation_id,
                observations=[
                    observation(
                        correlation_id=correlation_id,
                        attempt_index=0,
                        succeeded=False,
                        failure_kind="provider_error",
                    )
                ],
            )

        reports = await CapabilityReliabilityService(
            db,
            policy=CapabilityReliabilityPolicy(
                minimum_attempts=10,
            ),
        ).summarize(
            user_id=str(first_user),
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
            tenant_id="tenant_1",
        )

    assert len(reports) == 1

    report = reports[0]

    assert report.attempts == 10
    assert report.successes == 9
    assert report.failures == 1
    assert report.timeouts == 1
    assert report.provider_errors == 0
    assert report.success_rate == 0.9
    assert report.recommendation == (
        CapabilityReliabilityRecommendation.DEGRADED
    )


@pytest.mark.asyncio
async def test_reliability_summary_measures_fallback_recovery():
    user_id = uuid4()
    correlation_id = f"fallback-{uuid4()}"

    async with SessionLocal() as db:
        await record_observations(
            db=db,
            user_id=user_id,
            correlation_id=correlation_id,
            observations=[
                observation(
                    correlation_id=correlation_id,
                    attempt_index=0,
                    succeeded=False,
                    provider_id="shopify",
                    failure_kind="timeout",
                    fallback_allowed=True,
                    fallback_used=True,
                    final_attempt=False,
                ),
                observation(
                    correlation_id=correlation_id,
                    attempt_index=1,
                    succeeded=True,
                    provider_id="mock",
                    fallback_used=True,
                    final_attempt=True,
                ),
            ],
        )

        reports = await CapabilityReliabilityService(
            db,
            policy=CapabilityReliabilityPolicy(
                minimum_attempts=1,
            ),
        ).summarize(
            user_id=str(user_id),
            capability_id="ecommerce.orders.get",
            provider_id="shopify",
        )

    assert len(reports) == 1
    assert reports[0].fallback_eligible_failures == 1
    assert reports[0].fallback_recoveries == 1
    assert reports[0].fallback_recovery_rate == 1.0
