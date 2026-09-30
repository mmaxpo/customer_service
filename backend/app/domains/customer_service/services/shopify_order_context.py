from __future__ import annotations

from app.domains.customer_service.schemas.shopify_order_context import (
    ShopifyOrderContext,
    ShopifyTrackingInfo,
)


class ShopifyOrderContextBuilder:
    def build(self, order: dict) -> ShopifyOrderContext:
        financial_status = order.get("financial_status")
        # Shopify returns a null fulfillment status for unfulfilled orders in
        # some Admin API responses (and older cached payloads). Treat that as
        # the explicit unfulfilled state so Inbox actions and status cards do
        # not show an ambiguous "Unknown" value.
        fulfillment_status = order.get("fulfillment_status") or "unfulfilled"

        is_paid = financial_status == "paid"
        is_fulfilled = fulfillment_status == "fulfilled"

        tracking = ShopifyTrackingInfo(
            tracking_number=(
                order.get("tracking_number")
                or self._first_fulfillment_value(order, "tracking_number")
            ),
            tracking_url=(
                order.get("tracking_url")
                or self._first_fulfillment_value(order, "tracking_url")
            ),
            carrier=(
                order.get("carrier")
                or order.get("tracking_company")
                or self._first_fulfillment_value(order, "tracking_company")
            ),
            status=fulfillment_status,
        )

        return ShopifyOrderContext(
            order_id=str(order.get("id") or order.get("order_id")),
            order_name=order.get("name") or order.get("order_name"),
            customer_email=order.get("email") or order.get("customer_email"),
            financial_status=financial_status,
            fulfillment_status=fulfillment_status,
            total_price=str(order.get("total_price"))
            if order.get("total_price") is not None
            else None,
            currency=order.get("currency"),
            shipping_address=order.get("shipping_address"),
            tracking=tracking,
            is_paid=is_paid,
            is_fulfilled=is_fulfilled,
            can_refund=is_paid,
            can_cancel=not is_fulfilled,
            can_change_address=not is_fulfilled,
            raw=order,
        )

    def _first_fulfillment_value(self, order: dict, key: str):
        fulfillments = order.get("fulfillments") or []

        if not isinstance(fulfillments, list):
            return None

        for fulfillment in fulfillments:
            if isinstance(fulfillment, dict) and fulfillment.get(key):
                return fulfillment.get(key)

        return None
