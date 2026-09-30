from app.runtime.capabilities.registry.policies import (
    AllowDenyPolicy,
    ResolutionContext,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_allowed_provider_filters_candidates():

    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="orders.lookup",
            allowed_provider_ids=("mock",),
        ),
        candidates=[
            ProviderBinding(
                capability_id="orders.lookup",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            ),
            ProviderBinding(
                capability_id="orders.lookup",
                provider_id="mock",
                provider_ref="mock.get_order",
            ),
        ],
    )

    AllowDenyPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == ["mock"]
    assert ctx.rejected[0].reason == "not_in_allowed_providers"


def test_denied_provider_filters_candidates():

    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="orders.lookup",
            denied_provider_ids=("shopify",),
        ),
        candidates=[
            ProviderBinding(
                capability_id="orders.lookup",
                provider_id="shopify",
                provider_ref="shopify.get_order",
            ),
            ProviderBinding(
                capability_id="orders.lookup",
                provider_id="mock",
                provider_ref="mock.get_order",
            ),
        ],
    )

    AllowDenyPolicy().apply(ctx)

    assert [x.provider_id for x in ctx.candidates] == ["mock"]
    assert ctx.rejected[0].reason == "provider_denied"
