from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.events.event_store import PlatformEventStore
from app.platform.jobs.repository import JobRepository
from app.platform.jobs.worker import JobWorker
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceObservation,
    CapabilityPerformanceObservationStatus,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)


@pytest.mark.asyncio
async def test_health_evaluation_job_runs_idempotently():
    user_id = uuid4()
    window_end = datetime.now(timezone.utc)

    async with SessionLocal() as db:
        for index in range(10):
            correlation_id = f"health-job-{uuid4()}"
            event = await PlatformEventStore(db).append(
                user_id=user_id,
                event_type=("runtime.capability.execution.completed"),
                source="runtime.capabilities",
                payload={},
                meta={"correlation_id": correlation_id},
            )

            succeeded = index != 0

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
                        status=(
                            CapabilityPerformanceObservationStatus.SUCCEEDED
                            if succeeded
                            else CapabilityPerformanceObservationStatus.FAILED
                        ),
                        succeeded=succeeded,
                        duration_ms=10.0,
                        failure_kind=(None if succeeded else "timeout"),
                        tenant_id="tenant_1",
                        observed_at_ts=(
                            window_end - timedelta(minutes=index + 1)
                        ).timestamp(),
                    )
                ],
            )

        payload = {
            "user_id": str(user_id),
            "tenant_id": "tenant_1",
            "capability_id": "ecommerce.orders.get",
            "provider_id": "shopify",
            "provider_ref": "shopify.get_order",
            "window_hours": 1,
            "window_end": window_end.isoformat(),
            "minimum_attempts": 10,
        }

        first_job = await JobRepository(db).enqueue(
            user_id=user_id,
            job_type="capability.health.evaluate",
            payload=payload,
            max_attempts=5,
        )

        first_saved = await JobWorker(
            db,
            worker_id="health-evaluation-worker",
        ).run_once(job_id=first_job.id)

        second_job = await JobRepository(db).enqueue(
            user_id=user_id,
            job_type="capability.health.evaluate",
            payload=payload,
            max_attempts=5,
        )

        second_saved = await JobWorker(
            db,
            worker_id="health-evaluation-worker",
        ).run_once(job_id=second_job.id)

    assert first_saved.status == "succeeded"
    assert first_saved.result["status"] == "evaluated"
    assert first_saved.result["persistence"]["inserted"] is True

    assert second_saved.status == "succeeded"
    assert second_saved.result["persistence"]["inserted"] is False


@pytest.mark.asyncio
async def test_health_job_rejects_user_ownership_mismatch():
    owner_id = uuid4()
    payload_user_id = uuid4()

    async with SessionLocal() as db:
        job = await JobRepository(db).enqueue(
            user_id=owner_id,
            job_type="capability.health.evaluate",
            payload={
                "user_id": str(payload_user_id),
                "tenant_id": "tenant_1",
                "capability_id": "ecommerce.orders.get",
                "provider_id": "shopify",
                "window_hours": 1,
                "window_end": (datetime.now(timezone.utc).isoformat()),
            },
            max_attempts=1,
        )

        saved = await JobWorker(
            db,
            worker_id="health-evaluation-worker",
        ).run_once(job_id=job.id)

    assert saved.status == "dead_letter"
    assert "does not match job ownership" in (saved.error_message or "")
