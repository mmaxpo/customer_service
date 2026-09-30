import pytest

from app.runtime.resources import RuntimeServiceFactory


class FakeShopify:
    async def get_order(self, *, user_id, order_ref):
        return {
            "user_id": str(user_id),
            "order_name": order_ref,
            "source": "fake_shopify",
        }


@pytest.mark.asyncio
async def test_capability_invoker_resolves_shopify_get_order():
    services = RuntimeServiceFactory.build(
        user_id="user_1",
    )
    services.business.shopify = FakeShopify()

    result = await services.capabilities.invoke(
        "shopify.get_order",
        payload={"order_ref": "#1001"},
    )

    assert result["user_id"] == "user_1"
    assert result["order_name"] == "#1001"
    assert result["source"] == "fake_shopify"


@pytest.mark.asyncio
async def test_capability_invoker_requires_known_capability():
    services = RuntimeServiceFactory.build(user_id="user_1")

    with pytest.raises(ValueError, match="No capability resolver registered"):
        await services.capabilities.invoke("unknown.capability")
