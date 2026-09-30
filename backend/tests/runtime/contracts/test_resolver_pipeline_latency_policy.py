from app.runtime.capabilities.registry.policies import (
    LatencyPolicy,
    ResolutionContext,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_latency_policy_filters_slow_provider():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="ai.generate",
            max_latency_ms=500,
        ),
        candidates=[
            ProviderBinding(
                capability_id="ai.generate",
                provider_id="slow",
                provider_ref="slow.generate",
                metadata={"latency_ms": 2000},
            ),
            ProviderBinding(
                capability_id="ai.generate",
                provider_id="fast",
                provider_ref="fast.generate",
                metadata={"latency_ms": 200},
            ),
        ],
    )

    LatencyPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == ["fast"]
    assert ctx.rejected[0].provider_id == "slow"
    assert ctx.rejected[0].reason == "latency_exceeds_limit"
