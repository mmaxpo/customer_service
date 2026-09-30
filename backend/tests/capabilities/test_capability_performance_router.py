from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.platform.events.event_store import PlatformEventStore
from app.api.auth import get_current_user
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceObservation,
    CapabilityPerformanceObservationStatus,
)
from app.runtime.capabilities.execution.performance.repository import (
    CapabilityPerformanceObservationRepository,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


@pytest.mark.asyncio
async def test_capability_performance_routes_scope_to_current_user():
    current_user_id = uuid4()
    other_user_id = uuid4()
    correlation_id = f"api-{uuid4()}"

    async with SessionLocal() as db:
        event = await PlatformEventStore(db).append(
            user_id=current_user_id,
            event_type="runtime.capability.execution.completed",
            source="runtime.capabilities",
            payload={},
            meta={"correlation_id": correlation_id},
        )

        await CapabilityPerformanceObservationRepository(
            db
        ).record_many(
            source_event_id=event.id,
            observations=[
                CapabilityPerformanceObservation(
                    correlation_id=correlation_id,
                    attempt_index=0,
                    requested_capability_id="shopify.get_order",
                    resolved_capability_id="ecommerce.orders.get",
                    provider_id="shopify",
                    provider_ref="shopify.get_order",
                    status=(
                        CapabilityPerformanceObservationStatus
                        .SUCCEEDED
                    ),
                    succeeded=True,
                    duration_ms=5.0,
                    tenant_id="tenant_1",
                    observed_at_ts=datetime.now(
                        timezone.utc
                    ).timestamp(),
                )
            ],
        )

        other_event = await PlatformEventStore(db).append(
            user_id=other_user_id,
            event_type="runtime.capability.execution.completed",
            source="runtime.capabilities",
            payload={},
            meta={},
        )

        await CapabilityPerformanceObservationRepository(
            db
        ).record_many(
            source_event_id=other_event.id,
            observations=[
                CapabilityPerformanceObservation(
                    correlation_id=f"other-{uuid4()}",
                    attempt_index=0,
                    requested_capability_id="shopify.get_order",
                    resolved_capability_id="ecommerce.orders.get",
                    provider_id="shopify",
                    provider_ref="shopify.get_order",
                    status=(
                        CapabilityPerformanceObservationStatus
                        .FAILED
                    ),
                    succeeded=False,
                    failure_kind="provider_error",
                    tenant_id="tenant_1",
                    observed_at_ts=datetime.now(
                        timezone.utc
                    ).timestamp(),
                )
            ],
        )

    app.dependency_overrides[get_current_user] = (
        lambda: FakeUser(current_user_id)
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            summary = await client.get(
                "/capabilities/performance/summary",
                params={
                    "capability_id": "ecommerce.orders.get",
                    "provider_id": "shopify",
                    "minimum_attempts": 1,
                },
            )

            assert summary.status_code == 200
            assert len(summary.json()) == 1
            assert summary.json()[0]["attempts"] == 1
            assert summary.json()[0]["successes"] == 1

            observations = await client.get(
                "/capabilities/performance/observations",
                params={
                    "correlation_id": correlation_id,
                },
            )

            assert observations.status_code == 200
            assert len(
                observations.json()["items"]
            ) == 1
            assert (
                observations.json()["items"][0]
                ["correlation_id"]
                == correlation_id
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
