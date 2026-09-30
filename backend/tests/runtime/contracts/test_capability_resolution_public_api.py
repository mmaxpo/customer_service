from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
)
from app.runtime.capabilities.registry.defaults import (
    build_default_system,
)
from app.runtime.capabilities.registry.resolution import (
    CapabilityResolver,
    ResolutionContext,
    ResolverPipeline,
    SelectionPolicy,
)


def test_resolution_public_api_exports_operational_types():
    assert CapabilityResolver.__module__.endswith(
        ".capabilities.registry.resolution"
    )
    assert ResolverPipeline.__module__.endswith(
        ".capabilities.registry.resolution"
    )
    assert ResolutionContext.__module__.endswith(
        ".capabilities.registry.policies.base"
    )
    assert SelectionPolicy.__module__.endswith(
        ".capabilities.registry.policies.selection"
    )


def test_resolution_public_api_resolves_default_capability():
    resolver = build_default_system().build_resolver()

    assert isinstance(resolver, CapabilityResolver)

    result = resolver.resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.get"
    assert result.selected_provider_id == "shopify"
