from types import SimpleNamespace

import pytest

from app.runtime.capabilities.models import (
    CapabilityInvocation,
)
from app.runtime.capabilities.execution import (
    CapabilityExecutorRegistry,
)
from app.runtime.capabilities.resolver import CapabilityResolver
from app.runtime.capabilities.registry import (
    build_default_system,
)


@pytest.mark.asyncio
async def test_runtime_bridge_dispatches_through_registered_executor():
    services = SimpleNamespace(
        identity=SimpleNamespace(
            user_id="user_1",
            tenant_id=None,
        ),
        business=SimpleNamespace(),
    )

    registry = CapabilityExecutorRegistry()
    calls = []

    async def executor(context):
        calls.append(context)
        return {
            "provider": context.resolution.selected_provider_id,
            "order_ref": context.invocation.inputs["order_ref"],
        }

    registry.register("shopify.get_order", executor)

    resolver = CapabilityResolver(
        services=services,
        system=build_default_system(),
        executor_registry=registry,
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is True
    assert result.output == {
        "provider": "shopify",
        "order_ref": "#1001",
    }
    assert len(calls) == 1
    assert calls[0].services is services
    assert calls[0].resolution.provider_ref == "shopify.get_order"


@pytest.mark.asyncio
async def test_runtime_bridge_returns_stable_error_for_missing_executor():
    services = SimpleNamespace(
        identity=SimpleNamespace(
            user_id="user_1",
            tenant_id=None,
        ),
        business=SimpleNamespace(),
    )

    resolver = CapabilityResolver(
        services=services,
        system=build_default_system(),
        executor_registry=CapabilityExecutorRegistry(),
    )

    result = await resolver.resolve(
        CapabilityInvocation(
            capability_id="ecommerce.orders.get",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert result.error_code == "provider_executor_not_registered"
    assert (
        "No runtime provider executor registered for shopify.get_order"
        in result.error_message
    )
