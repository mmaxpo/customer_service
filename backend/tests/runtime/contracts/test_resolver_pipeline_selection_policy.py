from app.runtime.capabilities.registry.policies import (
    ResolutionContext,
    SelectionPolicy,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def make_binding(provider_id: str, priority: int) -> ProviderBinding:
    return ProviderBinding(
        capability_id="ecommerce.orders.get",
        provider_id=provider_id,
        provider_ref=f"{provider_id}.get_order",
        priority=priority,
    )


def test_selection_policy_uses_highest_priority():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
        ),
        candidates=[
            make_binding("mock", 10),
            make_binding("shopify", 100),
        ],
    )

    SelectionPolicy().apply(ctx)

    assert ctx.selected is not None
    assert ctx.selected.provider_id == "shopify"

    rejected = {
        item.provider_id: item.reason
        for item in ctx.rejected
    }
    assert rejected["mock"] == "lower_priority"


def test_selection_policy_honors_available_preferred_provider():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            preferred_provider_id="mock",
        ),
        candidates=[
            make_binding("shopify", 100),
            make_binding("mock", 10),
        ],
    )

    SelectionPolicy().apply(ctx)

    assert ctx.selected is not None
    assert ctx.selected.provider_id == "mock"

    rejected = {
        item.provider_id: item.reason
        for item in ctx.rejected
    }
    assert rejected["shopify"] == "lower_priority"


def test_selection_policy_is_deterministic_for_equal_priority():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
        ),
        candidates=[
            make_binding("zzz", 50),
            make_binding("aaa", 50),
        ],
    )

    SelectionPolicy().apply(ctx)

    assert ctx.selected is not None
    assert ctx.selected.provider_id == "aaa"


def test_selection_policy_handles_empty_candidates():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
        ),
        candidates=[],
    )

    SelectionPolicy().apply(ctx)

    assert ctx.selected is None
    assert ctx.rejected == []
