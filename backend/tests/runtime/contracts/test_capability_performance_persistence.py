from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.jobs.worker import JobWorker
from app.runtime.capabilities.execution import (
    CAPABILITY_EXECUTION_COMPLETED_EVENT,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)


@pytest.mark.asyncio
async def test_capability_event_projects_attempts_idempotently():
    correlation_id = f"cap-perf-{uuid4()}"
    user_id = uuid4()

    async with SessionLocal() as db:
        result = await PlatformEventPublisher(db).publish(
            user_id=user_id,
            event_type=CAPABILITY_EXECUTION_COMPLETED_EVENT,
            source="runtime.capabilities",
            payload={
                "requested_capability_id": "shopify.get_order",
                "resolved_capability_id": "ecommerce.orders.get",
                "status": "succeeded",
                "ok": True,
                "selected_provider_id": "mock",
                "provider_ref": "mock.get_order",
                "fallback_used": True,
                "attempts": [
                    {
                        "provider_id": "shopify",
                        "provider_ref": "shopify.get_order",
                        "capability_id": "ecommerce.orders.get",
                        "outcome": "error",
                        "failure_kind": "timeout",
                        "fallback_allowed": True,
                    },
                    {
                        "provider_id": "mock",
                        "provider_ref": "mock.get_order",
                        "capability_id": "ecommerce.orders.get",
                        "outcome": "success",
                    },
                ],
            },
            meta={
                "correlation_id": correlation_id,
                "tenant_id": "tenant_1",
            },
            dispatch=True,
        )

        event = result["event"]

        projection_results = [
            item
            for item in result["handler_results"]
            if item.get("job_type") == "capability.performance.project"
        ]
        assert len(projection_results) == 1

        job_id = projection_results[0]["enqueued_job_id"]

        saved = await JobWorker(
            db,
            worker_id="capability-test-worker",
        ).run_once(job_id=job_id)

        assert saved.status == "succeeded"
        assert saved.result["projected_count"] == 2
        assert saved.result["inserted_count"] == 2

        rows = await CapabilityPerformanceObservationRepository(db).list_for_event(
            source_event_id=event.id
        )

        assert len(rows) == 2
        assert rows[0].provider_id == "shopify"
        assert rows[0].failure_kind == "timeout"
        assert rows[1].provider_id == "mock"

        # Re-run the projector directly to prove insert idempotency.
        from app.runtime.capabilities.execution.performance.projection import (
            DurableCapabilityPerformanceProjector,
        )

        replay = await DurableCapabilityPerformanceProjector(
            repository=CapabilityPerformanceObservationRepository(db)
        ).project_event(event)

        assert replay["projected_count"] == 2
        assert replay["inserted_count"] == 0
        assert replay["duplicate_count"] == 2
