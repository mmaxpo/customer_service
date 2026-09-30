import pytest

from app.domains.customer_service.providers.commerce_defaults import (
    build_default_commerce_order_adapter_registry,
)
from app.domains.customer_service.services.support.commerce.customer_support_commerce_context import (
    CustomerSupportCommerceContextService,
)
from app.runtime.capabilities.models import (
    CapabilityInvocationStatus,
    CapabilityResult,
)


class FakeCapabilities:
    def __init__(self, result):
        self.result = result
        self.invocation = None

    async def resolve(self, invocation):
        self.invocation = invocation
        return self.result


@pytest.mark.asyncio
async def test_commerce_context_resolves_semantic_order_capability():
    capabilities = FakeCapabilities(
        CapabilityResult(
            status=CapabilityInvocationStatus.OK,
            capability_id="ecommerce.orders.get",
            output={
                "payload": {
                    "id": "123",
                    "name": "#1001",
                    "financial_status": "paid",
                    "fulfillment_status": "fulfilled",
                    "line_items": [
                        {
                            "id": "10",
                            "title": "Snowboard",
                            "quantity": 1,
                        }
                    ],
                }
            },
            metadata={
                "selected_provider_id": "shopify",
                "provider_ref": "shopify.get_order",
            },
        )
    )

    service = CustomerSupportCommerceContextService(
        capabilities=capabilities,
        commerce_adapters=(
            build_default_commerce_order_adapter_registry()
        ),
    )

    result = await service.get_order(
        user_id="user-1",
        order_ref="#1001",
    )

    assert result.found is True
    assert result.order is not None
    assert result.order.provider == "shopify"
    assert result.order.order_ref == "#1001"
    assert result.order.line_items[0].title == "Snowboard"

    assert capabilities.invocation.capability_id == "ecommerce.orders.get"
    assert capabilities.invocation.inputs == {
        "order_ref": "#1001"
    }
    assert capabilities.invocation.user_id == "user-1"


@pytest.mark.asyncio
async def test_commerce_context_preserves_order_not_found():
    capabilities = FakeCapabilities(
        CapabilityResult(
            status=CapabilityInvocationStatus.OK,
            capability_id="ecommerce.orders.get",
            output={
                "found": False,
                "order_ref": "#9999",
                "payload": None,
                "summary": {
                    "customer_safe_note": (
                        "I couldn't find order #9999. "
                        "Please check the order number and try again."
                    )
                },
            },
            metadata={
                "selected_provider_id": "shopify",
                "provider_ref": "shopify.get_order",
            },
        )
    )

    result = await CustomerSupportCommerceContextService(
        capabilities=capabilities,
        commerce_adapters=(
            build_default_commerce_order_adapter_registry()
        ),
    ).get_order(
        user_id="user-1",
        order_ref="#9999",
    )

    assert result.found is False
    assert result.order is None
    assert result.order_ref == "#9999"
    assert result.provider_id == "shopify"
    assert result.provider_ref == "shopify.get_order"
    assert "couldn't find order #9999" in result.customer_safe_note
