from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.runtime.capabilities.execution import (
    CapabilityPerformanceProjector,
)
from app.runtime.capabilities.execution.performance.projection import (
    capability_outcome_from_platform_event,
)


def test_capability_outcome_reconstructed_from_platform_event():
    event = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
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
            "created_at_ts": 123.0,
        },
        meta={
            "correlation_id": "corr_1",
            "tenant_id": "tenant_1",
            "workflow_run_id": "run_1",
            "invocation_metadata": {
                "planner_session_id": "planner_1",
            },
        },
        created_at=datetime.now(timezone.utc),
    )

    outcome = capability_outcome_from_platform_event(
        event
    )
    observations = CapabilityPerformanceProjector().project(
        outcome
    )

    assert outcome.correlation_id == "corr_1"
    assert outcome.tenant_id == "tenant_1"
    assert outcome.invocation_metadata[
        "workflow_run_id"
    ] == "run_1"
    assert len(observations) == 2
    assert observations[0].provider_id == "shopify"
    assert observations[1].provider_id == "mock"
