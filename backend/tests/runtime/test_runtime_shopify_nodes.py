import pytest

from app.providers.shopify.runtime.nodes import (
    ShopifyGetOrderConfig,
    ShopifyGetOrderNode,
    ShopifyOrderActionConfig,
    ShopifyOrderActionNode,
)


class Ctx:
    db = object()
    user_id = "user-1"


@pytest.mark.asyncio
async def test_shopify_get_order_requires_order_ref():
    with pytest.raises(ValueError):
        await ShopifyGetOrderNode().run(
            Ctx(),
            {"vars": {}},
            ShopifyGetOrderConfig(),
        )


@pytest.mark.asyncio
async def test_shopify_order_action_requires_order_ref():
    with pytest.raises(ValueError):
        await ShopifyOrderActionNode().run(
            Ctx(),
            {"vars": {}},
            ShopifyOrderActionConfig(action="refund"),
        )


class _RecordingShopifyService:
    def __init__(self):
        self.calls = []

    async def perform_order_action(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "ok", "order_id": "gid://shopify/Order/1"}


class _RecordingBusinessServices:
    def __init__(self, shopify):
        self.shopify = shopify


class _RecordingRuntimeServices:
    def __init__(self, shopify):
        self.business = _RecordingBusinessServices(shopify)


class _RecordingCtx:
    db = object()
    user_id = "user-1"
    thread_id = "thread-1"
    node_data = {"_runtime": {"idempotency_key": "idem-123"}}


@pytest.mark.asyncio
async def test_shopify_order_action_calls_perform_order_action_with_expected_kwargs(
    monkeypatch,
):
    shopify = _RecordingShopifyService()
    services = _RecordingRuntimeServices(shopify)

    monkeypatch.setattr(
        "app.providers.shopify.runtime.nodes.get_runtime_services",
        lambda ctx: services,
    )

    result = await ShopifyOrderActionNode().run(
        _RecordingCtx(),
        {"vars": {"order_ref": "#1001", "resume_input": {}}},
        ShopifyOrderActionConfig(action="reship", order_ref_from="vars"),
    )

    assert len(shopify.calls) == 1
    call = shopify.calls[0]
    assert call["action"] == "reship"
    assert call["order_ref"] == "#1001"
    assert call["idempotency_key"] == "idem-123"
    assert call["workflow_run_id"] == "thread-1"
    assert call["approval_wait_id"] is None
    assert result["output"]["status"] == "ok"
    assert result["meta"]["action"] == "reship"
