from app.runtime.capabilities.execution import (
    CapabilityExecutionAttempt,
    CapabilityExecutionOutcome,
    CapabilityExecutionOutcomeStatus,
    CapabilityPerformanceObservationStatus,
    CapabilityPerformanceProjector,
)


def test_projector_creates_one_observation_per_provider_attempt():
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
                duration_ms=5.0,
                error_code="capability_provider_timeout",
                failure_kind="timeout",
                exception_type="IntegrationTimeoutError",
                fallback_allowed=True,
            ),
            CapabilityExecutionAttempt(
                provider_id="mock",
                provider_ref="mock.get_order",
                capability_id="ecommerce.orders.get",
                outcome="success",
                duration_ms=2.0,
            ),
        ],
        user_id="user_1",
        tenant_id="tenant_1",
        invocation_metadata={
            "workflow_run_id": "run_1",
            "planner_session_id": "planner_1",
            "thread_id": "thread_1",
        },
        created_at_ts=123.0,
    )

    observations = CapabilityPerformanceProjector().project(
        outcome
    )

    assert len(observations) == 2

    first = observations[0]
    assert first.provider_id == "shopify"
    assert first.status == (
        CapabilityPerformanceObservationStatus.FAILED
    )
    assert first.succeeded is False
    assert first.failure_kind == "timeout"
    assert first.fallback_allowed is True
    assert first.fallback_used is True
    assert first.final_attempt is False

    second = observations[1]
    assert second.provider_id == "mock"
    assert second.status == (
        CapabilityPerformanceObservationStatus.SUCCEEDED
    )
    assert second.succeeded is True
    assert second.final_attempt is True

    assert second.workflow_run_id == "run_1"
    assert second.planner_session_id == "planner_1"
    assert second.thread_id == "thread_1"
    assert second.observed_at_ts == 123.0


def test_resolution_failure_without_provider_is_not_performance_evidence():
    outcome = CapabilityExecutionOutcome(
        correlation_id="corr_2",
        requested_capability_id="unknown.capability",
        status=CapabilityExecutionOutcomeStatus.FAILED,
        ok=False,
        error_code="unknown_capability",
    )

    observations = CapabilityPerformanceProjector().project(
        outcome
    )

    assert observations == []


def test_single_provider_outcome_without_attempts_is_projected():
    outcome = CapabilityExecutionOutcome(
        correlation_id="corr_3",
        requested_capability_id="example.read",
        resolved_capability_id="example.read",
        status=CapabilityExecutionOutcomeStatus.SUCCEEDED,
        ok=True,
        selected_provider_id="example",
        provider_ref="example.read",
        duration_ms=4.0,
    )

    observations = CapabilityPerformanceProjector().project(
        outcome
    )

    assert len(observations) == 1
    assert observations[0].provider_id == "example"
    assert observations[0].succeeded is True
    assert observations[0].final_attempt is True
