from app.runtime.capabilities.registry.contracts import (
    CapabilityResolutionRequest,
    CapabilityRisk,
)
from app.runtime.capabilities.registry.defaults import (
    build_default_system,
)


def test_default_system_registers_order_action_capability():
    system = build_default_system()

    capability = system.capabilities.get_capability(
        "ecommerce.orders.action"
    )

    assert capability.semantic_key == "order.action"
    assert capability.required_inputs == (
        "action",
        "order_ref",
    )
    assert capability.risk == CapabilityRisk.HIGH


def test_legacy_order_action_id_resolves_to_semantic_capability():
    system = build_default_system()

    result = system.build_resolver().resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.order_action",
            inputs={
                "action": "cancel",
                "order_ref": "#1001",
            },
        )
    )

    assert result.ok is True
    assert result.capability_id == "ecommerce.orders.action"
    assert result.selected_provider_id == "shopify"
    assert result.provider_ref == "shopify.order_action"
    assert result.requires_approval is True
    assert result.risk == CapabilityRisk.HIGH


def test_order_action_reports_missing_required_input():
    system = build_default_system()

    result = system.build_resolver().resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.order_action",
            inputs={
                "order_ref": "#1001",
            },
        )
    )

    assert result.ok is False
    assert result.capability_id == "ecommerce.orders.action"
    assert result.selected_provider_id == "shopify"
    assert result.missing_inputs == ("action",)


def test_order_action_constraint_accepts_supported_action():
    system = build_default_system()

    result = system.build_resolver().resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.order_action",
            required_action="refund",
            inputs={
                "action": "refund",
                "order_ref": "#1001",
            },
        )
    )

    assert result.ok is True
    assert result.provider_ref == "shopify.order_action"


def test_order_action_constraint_rejects_unsupported_action():
    system = build_default_system()

    result = system.build_resolver().resolve(
        CapabilityResolutionRequest(
            capability_id="shopify.order_action",
            required_action="delete_order",
            inputs={
                "action": "delete_order",
                "order_ref": "#1001",
            },
        )
    )

    assert result.ok is False
    assert result.capability_id == "ecommerce.orders.action"
    assert any(
        rejected.provider_id == "shopify"
        and rejected.reason == "action_not_supported"
        for rejected in result.rejected_providers
    )
