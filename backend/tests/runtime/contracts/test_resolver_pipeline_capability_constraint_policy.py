from app.runtime.capabilities.registry.policies import (
    CapabilityConstraintPolicy,
    ResolutionContext,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_capability_constraint_policy_filters_provider():

    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="orders.operation",
            required_action="refund",
        ),
        candidates=[
            ProviderBinding(
                capability_id="orders.operation",
                provider_id="lookup",
                provider_ref="lookup.operation",
                metadata={
                    "supported_actions": (
                        "lookup",
                    ),
                },
            ),
            ProviderBinding(
                capability_id="orders.operation",
                provider_id="full",
                provider_ref="full.operation",
                metadata={
                    "supported_actions": (
                        "lookup",
                        "refund",
                    ),
                },
            ),
        ],
    )

    CapabilityConstraintPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == [
        "full",
    ]

    assert ctx.rejected[0].provider_id == "lookup"
    assert ctx.rejected[0].reason == "action_not_supported"
