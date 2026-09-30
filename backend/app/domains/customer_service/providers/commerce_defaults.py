from __future__ import annotations

from app.domains.customer_service.providers.commerce import (
    CommerceOrderAdapterRegistry,
)
from app.domains.customer_service.providers.shopify_commerce import (
    ShopifyCommerceOrderAdapter,
)


def build_default_commerce_order_adapter_registry(
) -> CommerceOrderAdapterRegistry:
    registry = CommerceOrderAdapterRegistry()

    shopify = ShopifyCommerceOrderAdapter()

    registry.register(
        adapter=shopify,
        provider_id="shopify",
    )
    registry.register(
        adapter=shopify,
        provider_ref="shopify.get_order",
    )

    return registry


__all__ = [
    "build_default_commerce_order_adapter_registry",
]
