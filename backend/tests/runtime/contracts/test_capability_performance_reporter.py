import pytest

from app.runtime.capabilities.execution import (
    CapabilityExecutionAttempt,
    CapabilityExecutionOutcome,
    CapabilityExecutionOutcomeStatus,
    CapabilityPerformanceReporter,
    CompositeCapabilityOutcomeReporter,
    InMemoryCapabilityOutcomeReporter,
    InMemoryCapabilityPerformanceStore,
)


@pytest.mark.asyncio
async def test_performance_reporter_records_projected_attempts():
    store = InMemoryCapabilityPerformanceStore()
    reporter = CapabilityPerformanceReporter(
        store=store,
    )

    outcome = CapabilityExecutionOutcome(
        correlation_id="corr_1",
        requested_capability_id="shopify.get_order",
        resolved_capability_id="ecommerce.orders.get",
        status=CapabilityExecutionOutcomeStatus.SUCCEEDED,
        ok=True,
        fallback_used=True,
        attempts=[
            CapabilityExecutionAttempt(
                provider_id="shopify",
                provider_ref="shopify.get_order",
                capability_id="ecommerce.orders.get",
                outcome="error",
                failure_kind="timeout",
                fallback_allowed=True,
            ),
            CapabilityExecutionAttempt(
                provider_id="mock",
                provider_ref="mock.get_order",
                capability_id="ecommerce.orders.get",
                outcome="success",
            ),
        ],
    )

    await reporter.report(outcome)

    assert len(store.observations) == 2
    assert store.observations[0].provider_id == "shopify"
    assert store.observations[1].provider_id == "mock"


@pytest.mark.asyncio
async def test_performance_reporter_composes_with_existing_reporters():
    outcomes = InMemoryCapabilityOutcomeReporter()
    performance_store = InMemoryCapabilityPerformanceStore()

    reporter = CompositeCapabilityOutcomeReporter(
        [
            outcomes,
            CapabilityPerformanceReporter(
                store=performance_store,
            ),
        ]
    )

    outcome = CapabilityExecutionOutcome(
        correlation_id="corr_2",
        requested_capability_id="example.read",
        resolved_capability_id="example.read",
        status=CapabilityExecutionOutcomeStatus.SUCCEEDED,
        ok=True,
        selected_provider_id="example",
        provider_ref="example.read",
    )

    await reporter.report(outcome)

    assert len(outcomes.outcomes) == 1
    assert len(performance_store.observations) == 1
