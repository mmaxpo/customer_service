import pytest

from app.runtime.resources import RuntimeServiceFactory
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry.compatibility import (
    build_default_runtime_capability_registry,
)


def test_default_runtime_capability_registry_lists_allowed_capabilities():
    registry = build_default_runtime_capability_registry()

    assert registry.has("shopify.get_order")
    assert registry.has("shopify.order_action")

    get_order = registry.get("shopify.get_order")
    assert get_order.required_inputs == ("order_ref",)
    assert get_order.metadata["domain"] == "shopify"


def test_default_runtime_capability_registry_rejects_unknown():
    registry = build_default_runtime_capability_registry()

    with pytest.raises(ValueError, match="No capability resolver registered"):
        registry.get("unknown.capability")


@pytest.mark.asyncio
async def test_resolver_rejects_unknown_before_business_logic():
    services = RuntimeServiceFactory.build(user_id="user_1")

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="unknown.capability",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.error_code == "unknown_capability"


@pytest.mark.asyncio
async def test_resolver_uses_registry_required_inputs():
    services = RuntimeServiceFactory.build(user_id="user_1")

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.order_action",
            inputs={"action": "refund"},
        )
    )

    assert result.ok is False
    assert result.error_code == "missing_order_ref"
    assert "payload.order_ref" in result.error_message
