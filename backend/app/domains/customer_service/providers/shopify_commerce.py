from __future__ import annotations

from app.domains.customer_service.services.support.commerce.commerce_order import (
    CommerceLineItem,
    CommerceOrder,
)


class ShopifyCommerceOrderAdapter:
    """
    Translate Shopify provider data into the provider-neutral commerce
    contract used by customer-service interpretation and planning.
    """

    def adapt(self, order: dict) -> CommerceOrder:
        raw_items = order.get("line_items") or []
        line_items: list[CommerceLineItem] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            title = item.get("title") or item.get("name")

            if not title:
                continue

            line_items.append(
                CommerceLineItem(
                    provider_item_id=self._string(item.get("id")),
                    product_id=self._string(item.get("product_id")),
                    variant_id=self._string(item.get("variant_id")),
                    title=str(title),
                    variant_title=item.get("variant_title"),
                    sku=item.get("sku"),
                    quantity=self._quantity(item.get("quantity")),
                    fulfillment_status=item.get("fulfillment_status"),
                )
            )

        return CommerceOrder(
            provider="shopify",
            provider_order_id=str(
                order.get("id")
                or order.get("order_id")
                or ""
            ),
            order_ref=order.get("name") or order.get("order_name"),
            financial_status=order.get("financial_status"),
            fulfillment_status=order.get("fulfillment_status"),
            line_items=line_items,
        )

    def _string(self, value) -> str | None:
        if value is None:
            return None

        return str(value)

    def _quantity(self, value) -> int:
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            return 1

        return max(quantity, 1)
