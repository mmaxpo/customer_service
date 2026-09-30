from app.runtime.capabilities.registry.policies import (
    RegionPolicy,
    ResolutionContext,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_region_policy_filters_unsupported_region():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="data.store",
            required_region="eu",
        ),
        candidates=[
            ProviderBinding(
                capability_id="data.store",
                provider_id="us_provider",
                provider_ref="us.store",
                metadata={"regions": ("us",)},
            ),
            ProviderBinding(
                capability_id="data.store",
                provider_id="eu_provider",
                provider_ref="eu.store",
                metadata={"regions": ("eu",)},
            ),
        ],
    )

    RegionPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == ["eu_provider"]
    assert ctx.rejected[0].provider_id == "us_provider"
    assert ctx.rejected[0].reason == "region_not_supported"
