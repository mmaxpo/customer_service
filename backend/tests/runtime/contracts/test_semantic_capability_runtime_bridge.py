from types import SimpleNamespace

import pytest

from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.registry import (
    build_default_system,
)


class FakeShopify:
    def __init__(self):
        self.get_order_calls = []
        self.action_calls = []

    async def get_order(self, **kwargs):
        self.get_order_calls.append(kwargs)
        return {
            "id": "gid://shopify/Order/1001",
            "name": kwargs["order_ref"],
        }

    async def perform_order_action(self, **kwargs):
        self.action_calls.append(kwargs)
        return {
            "ok": True,
            "action": kwargs["action"],
            "order_ref": kwargs["order_ref"],
        }


def build_services():
    shopify = FakeShopify()

    services = SimpleNamespace(
        identity=SimpleNamespace(
            user_id="user_1",
            tenant_id=None,
        ),
        business=SimpleNamespace(
            shopify=shopify,
        ),
    )

    return services, shopify


@pytest.mark.asyncio
async def test_runtime_bridge_resolves_legacy_get_order_id():
    services, shopify = build_services()
    resolver = CapabilityResolver(
        services=services,
        system=build_default_system(),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.output["name"] == "#1001"
    assert result.metadata["resolved_capability_id"] == (
        "ecommerce.orders.get"
    )
    assert result.metadata["selected_provider_id"] == "shopify"
    assert result.metadata["provider_ref"] == "shopify.get_order"
    assert shopify.get_order_calls == [
        {
            "user_id": "user_1",
            "order_ref": "#1001",
        }
    ]


@pytest.mark.asyncio
async def test_runtime_bridge_accepts_semantic_capability_id():
    services, _ = build_services()
    resolver = CapabilityResolver(
        services=services,
        system=build_default_system(),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1002"},
        )
    )

    assert result.ok is True
    assert result.metadata["resolved_capability_id"] == (
        "ecommerce.orders.get"
    )


@pytest.mark.asyncio
async def test_runtime_bridge_executes_selected_order_action_provider():
    services, shopify = build_services()
    resolver = CapabilityResolver(
        services=services,
        system=build_default_system(),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="shopify.order_action",
            inputs={
                "action": "cancel",
                "order_ref": "#1001",
                "reason": "Customer requested cancellation",
            },
        )
    )

    assert result.ok is True
    assert result.output["action"] == "cancel"
    assert result.metadata["resolved_capability_id"] == (
        "ecommerce.orders.action"
    )
    assert result.metadata["provider_ref"] == (
        "shopify.order_action"
    )
    assert result.metadata["requires_approval"] is True
    assert shopify.action_calls[0]["user_id"] == "user_1"


@pytest.mark.asyncio
async def test_runtime_bridge_returns_semantic_missing_input_error():
    services, shopify = build_services()
    resolver = CapabilityResolver(
        services=services,
        system=build_default_system(),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.error_code == "missing_order_ref"
    assert result.metadata["resolved_capability_id"] == (
        "ecommerce.orders.get"
    )
    assert shopify.get_order_calls == []


@pytest.mark.asyncio
async def test_runtime_bridge_returns_unknown_capability_error():
    services, _ = build_services()
    resolver = CapabilityResolver(
        services=services,
        system=build_default_system(),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="unknown.capability",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.error_code == "unknown_capability"
    assert result.metadata["resolved_capability_id"] == (
        "unknown.capability"
    )
