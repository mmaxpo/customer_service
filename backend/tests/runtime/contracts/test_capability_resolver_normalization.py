import pytest

from app.runtime.resources import RuntimeServiceFactory
from app.runtime.capabilities.models import (
    CapabilityInvocation,
    CapabilityInvocationStatus,
)


class FakeShopify:
    async def get_order(self, *, user_id, order_ref):
        return {
            "user_id": str(user_id),
            "order_name": order_ref,
        }


@pytest.mark.asyncio
async def test_capability_resolver_returns_capability_result_on_resolve():
    services = RuntimeServiceFactory.build(user_id="user_1")
    services.business.shopify = FakeShopify()

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
            metadata={"source": "contract_test"},
        )
    )

    assert result.ok is True
    assert result.status == CapabilityInvocationStatus.OK
    assert result.capability_id == "shopify.get_order"
    assert result.output["order_name"] == "#1001"
    assert result.duration_ms is not None
    assert result.duration_ms >= 0
    assert result.metadata["correlation_id"]
    assert result.metadata["source"] == "contract_test"


@pytest.mark.asyncio
async def test_capability_resolver_returns_error_result_for_missing_payload():
    services = RuntimeServiceFactory.build(user_id="user_1")
    services.business.shopify = FakeShopify()

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.status == CapabilityInvocationStatus.ERROR
    assert result.capability_id == "shopify.get_order"
    assert result.error_code == "missing_order_ref"
    assert "payload.order_ref" in result.error_message
    assert result.duration_ms is not None


@pytest.mark.asyncio
async def test_capability_invoker_invoke_keeps_raw_output_compatibility():
    services = RuntimeServiceFactory.build(user_id="user_1")
    services.business.shopify = FakeShopify()

    output = await services.capabilities.invoke(
        "shopify.get_order",
        payload={"order_ref": "#1001"},
    )

    assert output["order_name"] == "#1001"
