from app.runtime.capabilities.registry.defaults import (
    build_default_binding_registry_v3,
    build_default_capability_alias_registry_v3,
    build_default_capability_registry_v3,
    build_default_provider_registry_v3,
)
from app.runtime.capabilities.registry.resolution import CapabilityResolver
from app.runtime.capabilities.registry.contracts import CapabilityResolutionRequest


def build():
    return CapabilityResolver(
        capabilities=build_default_capability_registry_v3(),
        providers=build_default_provider_registry_v3(),
        bindings=build_default_binding_registry_v3(),
        aliases=build_default_capability_alias_registry_v3(),
    )


def test_allowed_provider_ids_forces_mock_provider():
    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            allowed_provider_ids=("mock",),
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "mock"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["shopify"] == "not_in_allowed_providers"


def test_denied_provider_ids_falls_back_to_mock():
    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            denied_provider_ids=("shopify",),
        )
    )

    assert result.ok is True
    assert result.selected_provider_id == "mock"

    rejected = {item.provider_id: item.reason for item in result.rejected_providers}
    assert rejected["shopify"] == "provider_denied"


def test_all_providers_denied_returns_no_enabled_binding():
    result = build().resolve(
        CapabilityResolutionRequest(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
            denied_provider_ids=("shopify", "mock"),
        )
    )

    assert result.ok is False
    assert result.selected_provider_id is None
    assert result.metadata["diagnostics"]["status"] == "no_enabled_binding"
