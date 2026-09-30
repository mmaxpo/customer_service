from __future__ import annotations

import pytest

from app.runtime.capabilities.execution import (
    CAPABILITY_EXECUTION_COMPLETED_EVENT,
    CAPABILITY_EXECUTION_EVENT_SOURCE,
    CapabilityExecutionAttempt,
    CapabilityExecutionOutcome,
    CapabilityExecutionOutcomeStatus,
    CompositeCapabilityOutcomeReporter,
    InMemoryCapabilityOutcomeReporter,
    PlatformCapabilityOutcomeReporter,
)


class RecordingPublisher:
    def __init__(self):
        self.calls = []

    async def publish(self, **kwargs):
        self.calls.append(kwargs)
        return {"event": {"id": "event_1"}}


class FailingReporter:
    async def report(self, outcome):
        raise RuntimeError("reporter failed")


@pytest.mark.asyncio
async def test_platform_reporter_publishes_stable_event_contract():
    publisher = RecordingPublisher()
    reporter = PlatformCapabilityOutcomeReporter(
        publisher=publisher,
    )

    outcome = CapabilityExecutionOutcome(
        correlation_id="corr_1",
        requested_capability_id="shopify.get_order",
        resolved_capability_id="ecommerce.orders.get",
        status=CapabilityExecutionOutcomeStatus.SUCCEEDED,
        ok=True,
        selected_provider_id="mock",
        provider_ref="mock.get_order",
        fallback_used=True,
        attempts=[
            CapabilityExecutionAttempt(
                provider_id="shopify",
                provider_ref="shopify.get_order",
                capability_id="ecommerce.orders.get",
                outcome="error",
                error_code="capability_provider_timeout",
                failure_kind="timeout",
                exception_type="IntegrationTimeoutError",
                fallback_allowed=True,
                duration_ms=5.0,
            ),
            CapabilityExecutionAttempt(
                provider_id="mock",
                provider_ref="mock.get_order",
                capability_id="ecommerce.orders.get",
                outcome="success",
                duration_ms=2.0,
            ),
        ],
        duration_ms=8.0,
        user_id="user_1",
        tenant_id="tenant_1",
        invocation_metadata={
            "workflow_run_id": "run_1",
            "planner_session_id": "planner_1",
            "thread_id": "thread_1",
        },
    )

    await reporter.report(outcome)

    assert len(publisher.calls) == 1
    call = publisher.calls[0]

    assert call["event_type"] == (
        CAPABILITY_EXECUTION_COMPLETED_EVENT
    )
    assert call["source"] == CAPABILITY_EXECUTION_EVENT_SOURCE
    assert call["dispatch"] is False
    assert call["user_id"] == "user_1"

    assert call["payload"]["status"] == "succeeded"
    assert call["payload"]["ok"] is True
    assert call["payload"]["fallback_used"] is True
    assert len(call["payload"]["attempts"]) == 2
    assert (
        call["payload"]["attempts"][0]["failure_kind"]
        == "timeout"
    )

    assert call["meta"]["correlation_id"] == "corr_1"
    assert call["meta"]["tenant_id"] == "tenant_1"
    assert call["meta"]["workflow_run_id"] == "run_1"
    assert (
        call["meta"]["planner_session_id"]
        == "planner_1"
    )
    assert call["meta"]["thread_id"] == "thread_1"


@pytest.mark.asyncio
async def test_platform_reporter_dispatch_can_be_enabled_explicitly():
    publisher = RecordingPublisher()
    reporter = PlatformCapabilityOutcomeReporter(
        publisher=publisher,
        dispatch=True,
    )

    outcome = CapabilityExecutionOutcome(
        correlation_id="corr_2",
        requested_capability_id="example.read",
        status=CapabilityExecutionOutcomeStatus.FAILED,
        ok=False,
        error_code="provider_unavailable",
    )

    await reporter.report(outcome)

    assert publisher.calls[0]["dispatch"] is True
    assert publisher.calls[0]["payload"]["status"] == "failed"
    assert publisher.calls[0]["payload"]["error_code"] == (
        "provider_unavailable"
    )


def test_platform_reporter_requires_explicit_publisher():
    with pytest.raises(ValueError, match="publisher is required"):
        PlatformCapabilityOutcomeReporter(
            publisher=None,
        )


@pytest.mark.asyncio
async def test_composite_reporter_isolates_reporter_failures():
    memory = InMemoryCapabilityOutcomeReporter()

    reporter = CompositeCapabilityOutcomeReporter(
        [
            FailingReporter(),
            memory,
        ]
    )

    outcome = CapabilityExecutionOutcome(
        correlation_id="corr_3",
        requested_capability_id="example.read",
        status=CapabilityExecutionOutcomeStatus.SUCCEEDED,
        ok=True,
    )

    await reporter.report(outcome)

    assert len(memory.outcomes) == 1
    assert memory.outcomes[0].correlation_id == "corr_3"


def test_composite_reporter_preserves_injection_order():
    first = InMemoryCapabilityOutcomeReporter()
    second = InMemoryCapabilityOutcomeReporter()

    reporter = CompositeCapabilityOutcomeReporter(
        [first, second]
    )

    assert reporter.reporters == (first, second)
