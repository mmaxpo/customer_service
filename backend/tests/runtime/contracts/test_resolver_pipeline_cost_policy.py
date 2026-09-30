from app.runtime.capabilities.registry.policies import (
    CostPolicy,
    ResolutionContext,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_cost_policy_filters_expensive_provider():

    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="ai.generate",
            max_cost=5,
        ),
        candidates=[
            ProviderBinding(
                capability_id="ai.generate",
                provider_id="gpt5",
                provider_ref="gpt5.generate",
                metadata={
                    "cost": 20,
                },
            ),
            ProviderBinding(
                capability_id="ai.generate",
                provider_id="glm",
                provider_ref="glm.generate",
                metadata={
                    "cost": 2,
                },
            ),
        ],
    )

    CostPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == [
        "glm",
    ]

    assert ctx.rejected[0].provider_id == "gpt5"
    assert ctx.rejected[0].reason == "cost_exceeds_limit"
