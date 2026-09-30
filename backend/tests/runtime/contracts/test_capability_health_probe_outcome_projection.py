from app.runtime.capabilities.execution.outcomes import (
    CapabilityExecutionAttempt,
    CapabilityExecutionOutcome,
)
from app.runtime.capabilities.execution.performance.models import (
    CapabilityPerformanceProjector,
)


def test_probe_fields_survive_outcome_projection():
    outcome = CapabilityExecutionOutcome(
        correlation_id="probe-outcome",
        requested_capability_id=(
            "ecommerce.orders.get"
        ),
        resolved_capability_id=(
            "ecommerce.orders.get"
        ),
        status="succeeded",
        ok=True,
        selected_provider_id="shopify",
        provider_ref="shopify.get_order",
        attempts=[
            CapabilityExecutionAttempt(
                provider_id="shopify",
                provider_ref="shopify.get_order",
                capability_id=(
                    "ecommerce.orders.get"
                ),
                outcome="success",
                health_probe=True,
                health_probe_lease_token=(
                    "probe-token"
                ),
            )
        ],
    )

    observations = (
        CapabilityPerformanceProjector()
        .project(outcome)
    )

    assert len(observations) == 1
    assert observations[0].health_probe is True
    assert (
        observations[0]
        .health_probe_lease_token
        == "probe-token"
    )
