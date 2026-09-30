from app.runtime.capabilities.registry.compatibility import (
    CapabilityProviderType,
    CapabilityRiskLevel,
    build_default_capability_registry_v2,
)


def test_capability_registry_v2_groups_core_capabilities_by_category():
    registry = build_default_capability_registry_v2()

    shopify_get_order = registry.get("shopify.get_order")

    assert shopify_get_order.category == "ecommerce.orders"
    assert shopify_get_order.provider_type == CapabilityProviderType.BUILTIN
    assert shopify_get_order.provider_ref == "shopify.get_order"
    assert shopify_get_order.required_inputs == ["order_ref"]
    assert shopify_get_order.risk_level == CapabilityRiskLevel.SAFE


def test_capability_registry_v2_marks_mutating_shopify_actions_as_approval_risk():
    registry = build_default_capability_registry_v2()

    action = registry.get("shopify.order_action")

    assert action.category == "ecommerce.orders"
    assert action.required_inputs == ["action", "order_ref"]
    assert action.requires_approval is True
    assert action.risk_level == CapabilityRiskLevel.HIGH


def test_capability_registry_v2_can_list_by_parent_category():
    registry = build_default_capability_registry_v2()

    ecommerce = registry.list(category="ecommerce")

    assert [item.id for item in ecommerce] == [
        "shopify.get_order",
        "shopify.order_action",
    ]


def test_capability_registry_v2_rejects_unknown_capability():
    registry = build_default_capability_registry_v2()

    try:
        registry.get("missing.capability")
    except ValueError as exc:
        assert "No capability resolver registered for missing.capability" in str(exc)
    else:
        raise AssertionError("Expected unknown capability to fail")
