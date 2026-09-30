import pytest

from app.runtime.capabilities.execution import (
    CapabilityExecutionAttempt,
    CapabilityExecutionOutcome,
    CapabilityExecutionOutcomeStatus,
    CapabilityPerformanceReporter,
    InMemoryCapabilityPerformanceStore,
)
from app.runtime.capabilities.registry.state import (
    ProviderHealthRegistry,
)


@pytest.mark.asyncio
async def test_performance_observation_does_not_mutate_provider_health():
    health = ProviderHealthRegistry()
    store = InMemoryCapabilityPerformanceStore()
    reporter = CapabilityPerformanceReporter(
        store=store,
    )

    await reporter.report(
        CapabilityExecutionOutcome(
            correlation_id="corr_1",
            requested_capability_id="shopify.get_order",
            resolved_capability_id="ecommerce.orders.get",
            status=CapabilityExecutionOutcomeStatus.FAILED,
            ok=False,
            selected_provider_id="shopify",
            provider_ref="shopify.get_order",
            attempts=[
                CapabilityExecutionAttempt(
                    provider_id="shopify",
                    provider_ref="shopify.get_order",
                    capability_id="ecommerce.orders.get",
                    outcome="error",
                    failure_kind="timeout",
                    fallback_allowed=True,
                )
            ],
        )
    )

    assert len(store.observations) == 1
    assert health.is_healthy("shopify") is True
