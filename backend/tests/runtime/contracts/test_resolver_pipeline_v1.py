from app.runtime.capabilities.registry.policies import (
    ResolutionContext,
    SelectionPolicy,
)
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


def test_selection_policy_selects_highest_priority_without_reordering_candidates():

    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(
            capability_id="x",
        ),
        candidates=[
            ProviderBinding(
                capability_id="x",
                provider_id="b",
                provider_ref="b",
                priority=50,
            ),
            ProviderBinding(
                capability_id="x",
                provider_id="a",
                provider_ref="a",
                priority=5,
            ),
            ProviderBinding(
                capability_id="x",
                provider_id="c",
                provider_ref="c",
                priority=100,
            ),
        ],
    )

    SelectionPolicy().apply(ctx)

    assert ctx.selected is not None
    assert ctx.selected.provider_id == "c"

    # Selection does not mutate candidate order.
    assert [candidate.provider_id for candidate in ctx.candidates] == [
        "b",
        "a",
        "c",
    ]

    rejected = {
        item.provider_id: item.reason
        for item in ctx.rejected
    }

    assert rejected == {
        "b": "lower_priority",
        "a": "lower_priority",
    }
