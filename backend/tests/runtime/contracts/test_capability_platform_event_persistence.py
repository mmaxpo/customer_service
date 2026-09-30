from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.platform.events.event_store import PlatformEventStore
from app.platform.events.publisher import PlatformEventPublisher
from app.runtime.capabilities.execution import (
    CAPABILITY_EXECUTION_COMPLETED_EVENT,
    CapabilityExecutionOutcome,
    CapabilityExecutionOutcomeStatus,
    PlatformCapabilityOutcomeReporter,
)


@pytest.mark.asyncio
async def test_platform_capability_reporter_persists_event_without_dispatch():
    user_id = uuid4()
    correlation_id = f"capability-event-{uuid4()}"

    async with SessionLocal() as db:
        reporter = PlatformCapabilityOutcomeReporter(
            publisher=PlatformEventPublisher(db),
        )

        await reporter.report(
            CapabilityExecutionOutcome(
                correlation_id=correlation_id,
                requested_capability_id="shopify.get_order",
                resolved_capability_id="ecommerce.orders.get",
                status=(
                    CapabilityExecutionOutcomeStatus.SUCCEEDED
                ),
                ok=True,
                selected_provider_id="shopify",
                provider_ref="shopify.get_order",
                user_id=str(user_id),
                tenant_id="tenant_1",
                invocation_metadata={
                    "workflow_run_id": "run_1",
                },
            )
        )

    async with SessionLocal() as db:
        events = await PlatformEventStore(db).list_by_type(
            event_type=CAPABILITY_EXECUTION_COMPLETED_EVENT,
            limit=50,
        )

    matching = [
        event
        for event in events
        if event.meta.get("correlation_id") == correlation_id
    ]

    assert matching

    event = matching[0]

    assert event.user_id == user_id
    assert event.source == "runtime.capabilities"
    assert event.payload["status"] == "succeeded"
    assert event.payload["provider_ref"] == (
        "shopify.get_order"
    )
    assert event.meta["tenant_id"] == "tenant_1"
    assert event.meta["workflow_run_id"] == "run_1"
