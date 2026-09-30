from app.runtime.capabilities.execution import (
    CapabilityPerformanceObservation,
    CapabilityPerformanceObservationStatus,
    InMemoryCapabilityPerformanceStore,
)


def observation(
    *,
    correlation_id,
    succeeded,
    duration_ms,
    failure_kind=None,
    fallback_allowed=False,
    fallback_used=False,
):
    return CapabilityPerformanceObservation(
        correlation_id=correlation_id,
        attempt_index=0,
        requested_capability_id="shopify.get_order",
        resolved_capability_id="ecommerce.orders.get",
        provider_id="shopify",
        provider_ref="shopify.get_order",
        status=(
            CapabilityPerformanceObservationStatus.SUCCEEDED
            if succeeded
            else CapabilityPerformanceObservationStatus.FAILED
        ),
        succeeded=succeeded,
        duration_ms=duration_ms,
        failure_kind=failure_kind,
        error_code=(
            f"capability_provider_{failure_kind}"
            if failure_kind
            else None
        ),
        fallback_allowed=fallback_allowed,
        fallback_used=fallback_used,
        tenant_id="tenant_1",
    )


def test_store_builds_provider_capability_summary():
    store = InMemoryCapabilityPerformanceStore()

    store.record_many(
        [
            observation(
                correlation_id="corr_1",
                succeeded=False,
                duration_ms=10.0,
                failure_kind="timeout",
                fallback_allowed=True,
                fallback_used=True,
            ),
            observation(
                correlation_id="corr_2",
                succeeded=True,
                duration_ms=4.0,
            ),
            observation(
                correlation_id="corr_3",
                succeeded=False,
                duration_ms=7.0,
                failure_kind="provider_error",
            ),
        ]
    )

    summaries = store.summarize(
        capability_id="ecommerce.orders.get",
        provider_id="shopify",
        tenant_id="tenant_1",
    )

    assert len(summaries) == 1

    summary = summaries[0]

    assert summary.attempts == 3
    assert summary.successes == 1
    assert summary.failures == 2
    assert summary.timeouts == 1
    assert summary.provider_errors == 1
    assert summary.fallback_eligible_failures == 1
    assert summary.fallback_invocations == 1
    assert summary.total_duration_ms == 21.0
    assert summary.average_duration_ms == 7.0
    assert summary.success_rate == 1 / 3
    assert summary.last_failure_kind == "provider_error"


def test_store_groups_tenants_independently():
    store = InMemoryCapabilityPerformanceStore()

    first = observation(
        correlation_id="corr_1",
        succeeded=True,
        duration_ms=3.0,
    )
    second = first.model_copy(
        update={
            "correlation_id": "corr_2",
            "tenant_id": "tenant_2",
        }
    )

    store.record_many([first, second])

    summaries = store.summarize()

    assert len(summaries) == 2
    assert {
        item.tenant_id for item in summaries
    } == {"tenant_1", "tenant_2"}
