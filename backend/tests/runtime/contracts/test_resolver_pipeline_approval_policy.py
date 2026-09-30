from app.runtime.capabilities.registry.policies import (
    ApprovalPolicy,
    ResolutionContext,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_approval_policy_filters_approval_required_provider():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="orders.refund",
            allow_approval_required=False,
        ),
        candidates=[
            ProviderBinding(
                capability_id="orders.refund",
                provider_id="approval",
                provider_ref="approval.refund",
                requires_approval=True,
            ),
            ProviderBinding(
                capability_id="orders.refund",
                provider_id="safe",
                provider_ref="safe.refund",
                requires_approval=False,
            ),
        ],
    )

    ApprovalPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == ["safe"]
    assert ctx.rejected[0].provider_id == "approval"
    assert ctx.rejected[0].reason == "approval_required"
