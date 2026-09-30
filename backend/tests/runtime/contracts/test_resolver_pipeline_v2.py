from app.runtime.capabilities.registry.resolution import ResolverPipeline
from app.runtime.capabilities.registry.policies import ResolutionContext
from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    ProviderBinding,
)


class RemoveProviderPolicy:
    def __init__(self, provider_id):
        self.provider_id = provider_id

    def apply(self, ctx):
        ctx.candidates = [
            item for item in ctx.candidates
            if item.provider_id != self.provider_id
        ]


def test_resolver_pipeline_runs_policies_in_order():
    ctx = ResolutionContext(
        request=CapabilityResolutionRequest(capability_id="x"),
        candidates=[
            ProviderBinding(capability_id="x", provider_id="a", provider_ref="a"),
            ProviderBinding(capability_id="x", provider_id="b", provider_ref="b"),
            ProviderBinding(capability_id="x", provider_id="c", provider_ref="c"),
        ],
    )

    ResolverPipeline(
        policies=[
            RemoveProviderPolicy("a"),
            RemoveProviderPolicy("c"),
        ]
    ).run(ctx)

    assert [item.provider_id for item in ctx.candidates] == ["b"]
