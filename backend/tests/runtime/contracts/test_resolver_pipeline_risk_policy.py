from app.runtime.capabilities.registry.policies import (
    ResolutionContext,
    RiskPolicy,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    CapabilityRisk,
    ProviderBinding,
)


def test_risk_policy_filters_high_risk_provider():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="orders.action",
            max_risk=CapabilityRisk.MEDIUM,
        ),
        candidates=[
            ProviderBinding(
                capability_id="orders.action",
                provider_id="highrisk",
                provider_ref="highrisk.action",
                risk=CapabilityRisk.HIGH,
            ),
            ProviderBinding(
                capability_id="orders.action",
                provider_id="safe",
                provider_ref="safe.action",
                risk=CapabilityRisk.SAFE,
            ),
        ],
    )

    RiskPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == ["safe"]
    assert ctx.rejected[0].provider_id == "highrisk"
    assert ctx.rejected[0].reason == "risk_exceeds_limit"
