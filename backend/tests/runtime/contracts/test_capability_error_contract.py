import pytest
from fastapi import HTTPException

from app.runtime.resources import RuntimeServiceFactory
from app.runtime.capabilities.models import (
    CapabilityInvocation,
)


class FakeShopifyConnectionMissing:
    async def get_order(self, *, user_id, order_ref):
        raise HTTPException(
            status_code=404,
            detail="No active Shopify connection found",
        )


class FakeShopifyOrderMissing:
    async def get_order(self, *, user_id, order_ref):
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )


@pytest.mark.asyncio
async def test_capability_resolver_maps_missing_order_ref_error():
    services = RuntimeServiceFactory.build(user_id="user_1")

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.error_code == "missing_order_ref"
    assert "payload.order_ref" in result.error_message


@pytest.mark.asyncio
async def test_capability_resolver_maps_unknown_capability_error():
    services = RuntimeServiceFactory.build(user_id="user_1")

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="unknown.capability",
            inputs={},
        )
    )

    assert result.ok is False
    assert result.error_code == "unknown_capability"
    assert "No capability resolver registered" in result.error_message


@pytest.mark.asyncio
async def test_capability_resolver_maps_shopify_connection_missing():
    services = RuntimeServiceFactory.build(user_id="user_1")
    services.business.shopify = FakeShopifyConnectionMissing()

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#1001"},
        )
    )

    assert result.ok is False
    assert result.error_code == "shopify_connection_not_found"
    assert result.error_message == "No active Shopify connection found"
    assert result.metadata["http_status_code"] == 404


@pytest.mark.asyncio
async def test_capability_resolver_maps_shopify_order_missing_as_business_result():
    services = RuntimeServiceFactory.build(user_id="user_1")
    services.business.shopify = FakeShopifyOrderMissing()

    result = await services.capabilities.resolve(
        CapabilityInvocation(
            capability_id="shopify.get_order",
            inputs={"order_ref": "#9999"},
        )
    )

    assert result.ok is True
    assert result.error_code is None
    assert result.error_message is None

    assert result.output["found"] is False
    assert result.output["order_ref"] == "#9999"
    assert result.output["order_id"] is None
    assert result.output["payload"] is None
    assert result.output["context"] is None

    summary = result.output["summary"]

    assert summary["found"] is False
    assert summary["order_ref"] == "#9999"
    assert summary["order_name"] == "#9999"
    assert summary["available_actions"] == {}
    assert (
        summary["customer_safe_note"]
        == "I couldn't find order #9999. "
        "Please check the order number and try again."
    )


@pytest.mark.asyncio
async def test_capability_invoker_keeps_exception_compatibility():
    services = RuntimeServiceFactory.build(user_id="user_1")

    with pytest.raises(ValueError, match="payload.order_ref"):
        await services.capabilities.invoke(
            "shopify.get_order",
            payload={},
        )
