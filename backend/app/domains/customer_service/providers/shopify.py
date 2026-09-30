from __future__ import annotations

from typing import Protocol


class ShopifyProvider(Protocol):
    async def create_app_subscription(self, **kwargs) -> dict: ...

    async def get_active_app_subscriptions(self, **kwargs) -> list[dict]: ...

    async def cancel_app_subscription(self, **kwargs) -> dict: ...

    async def verify_connection(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
    ) -> dict: ...

    async def get_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order_ref: str,
    ) -> dict | None: ...

    async def list_knowledge_content(
        self, *, shop_domain: str, access_token: str | None
    ) -> list[dict]: ...

    async def refund_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        amount: str | None,
        scope: dict | None = None,
    ) -> dict: ...

    async def cancel_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
    ) -> dict: ...

    async def change_order_address(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        new_address: dict,
        note: str | None,
    ) -> dict: ...

    async def reship_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        note: str | None,
        scope: dict | None = None,
    ) -> dict: ...

    async def report_damaged_item(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        note: str | None,
    ) -> dict: ...

    async def get_shipping_status(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
    ) -> dict: ...

    async def add_order_note(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        note: str,
    ) -> dict: ...


class FakeShopifyProvider:
    async def create_app_subscription(self, **kwargs) -> dict:
        return {
            "id": "gid://shopify/AppSubscription/fake",
            "confirmation_url": "https://example.myshopify.com/admin/charges/fake",
        }

    async def get_active_app_subscriptions(self, **kwargs) -> list[dict]:
        return []

    async def cancel_app_subscription(self, **kwargs) -> dict:
        return {"id": kwargs["subscription_id"], "status": "CANCELLED"}

    async def verify_connection(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
    ) -> dict:
        if not access_token:
            raise ValueError("Shopify access token is required")

        return {
            "id": "fake-shop",
            "name": "Fake Shopify Store",
            "myshopify_domain": shop_domain,
        }

    async def get_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order_ref: str,
    ) -> dict | None:
        return {
            "id": order_ref,
            "name": order_ref if str(order_ref).startswith("#") else f"#{order_ref}",
            "email": "customer@example.com",
            "financial_status": "paid",
            "fulfillment_status": "fulfilled",
            "total_price": "99.00",
            "currency": "EUR",
            "shop_domain": shop_domain,
        }

    async def list_knowledge_content(
        self, *, shop_domain: str, access_token: str | None
    ) -> list[dict]:
        return []

    async def refund_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        amount: str | None,
        scope: dict | None = None,
    ) -> dict:
        return {
            "status": "prepared",
            "message": "Refund request prepared for review",
            "reason": reason,
            "amount": amount,
            "scope": scope or {},
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
        }

    async def cancel_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
    ) -> dict:
        fulfillment_status = order.get("fulfillment_status")
        if fulfillment_status == "fulfilled":
            return {
                "status": "blocked",
                "message": "Order is already fulfilled and cannot be auto-cancelled",
                "reason": reason,
                "shop_domain": shop_domain,
                "order_id": str(order.get("id")),
            }

        return {
            "status": "prepared",
            "message": "Cancellation request prepared for review",
            "reason": reason,
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
        }

    async def change_order_address(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        new_address: dict,
        note: str | None,
    ) -> dict:
        if order.get("fulfillment_status") == "fulfilled":
            return {
                "status": "blocked",
                "message": "Order is already fulfilled and address cannot be changed automatically",
                "new_address": new_address,
                "note": note,
                "shop_domain": shop_domain,
                "order_id": str(order.get("id")),
            }

        return {
            "status": "prepared",
            "message": "Address change request prepared for review",
            "new_address": new_address,
            "note": note,
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
        }

    async def reship_order(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        note: str | None,
        scope: dict | None = None,
    ) -> dict:
        return {
            "status": "prepared",
            "message": "Replacement shipment prepared for review",
            "reason": reason,
            "note": note,
            "scope": scope or {},
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
        }

    async def report_damaged_item(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        reason: str | None,
        note: str | None,
    ) -> dict:
        return {
            "status": "prepared",
            "message": "Damaged item case prepared for support review",
            "reason": reason,
            "note": note,
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
        }

    async def get_shipping_status(
        self, *, shop_domain: str, access_token: str | None, order: dict
    ) -> dict:
        return {
            "status": "found",
            "message": "Shipping status found",
            "fulfillment_status": order.get("fulfillment_status"),
            "tracking_number": order.get("tracking_number"),
            "tracking_url": order.get("tracking_url"),
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
        }

    async def add_order_note(
        self,
        *,
        shop_domain: str,
        access_token: str | None,
        order: dict,
        note: str,
    ) -> dict:
        return {
            "status": "prepared",
            "message": "Order note prepared for review",
            "note": note,
            "shop_domain": shop_domain,
            "order_id": str(order.get("id")),
        }
