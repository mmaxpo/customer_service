from __future__ import annotations

from typing import Any

from app.domains.customer_service.schemas.shopify_order_context import (
    ShopifyOrderContext,
)


class ShopifySupportWorkflowDecisionService:
    def shipping_status(self, context: ShopifyOrderContext) -> dict[str, Any]:
        if context.tracking.tracking_number or context.tracking.tracking_url:
            return {
                "action": "shipping_status",
                "status": "ready",
                "message": "Shipping status is available.",
                "tracking": context.tracking.model_dump(mode="json"),
                "requires_approval": False,
            }

        return {
            "action": "shipping_status",
            "status": "needs_review",
            "message": "No tracking information is available for this order.",
            "tracking": context.tracking.model_dump(mode="json"),
            "requires_approval": True,
        }

    def refund(
        self, context: ShopifyOrderContext, *, reason: str | None = None
    ) -> dict[str, Any]:
        if not context.is_paid:
            return {
                "action": "refund",
                "status": "blocked",
                "message": "Order is not paid, so it cannot be refunded.",
                "reason": reason,
                "requires_approval": False,
            }

        return {
            "action": "refund",
            "status": "needs_approval",
            "message": "Refund can be prepared but requires approval before execution.",
            "reason": reason,
            "requires_approval": True,
        }

    def cancel(
        self, context: ShopifyOrderContext, *, reason: str | None = None
    ) -> dict[str, Any]:
        if context.is_fulfilled:
            return {
                "action": "cancel",
                "status": "blocked",
                "message": "Order is already fulfilled and cannot be cancelled automatically.",
                "reason": reason,
                "requires_approval": False,
            }

        return {
            "action": "cancel",
            "status": "needs_approval",
            "message": "Cancellation can be prepared but requires approval before execution.",
            "reason": reason,
            "requires_approval": True,
        }

    def change_address(
        self,
        context: ShopifyOrderContext,
        *,
        new_address: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        if context.is_fulfilled:
            return {
                "action": "change_address",
                "status": "blocked",
                "message": "Order is already fulfilled and address cannot be changed automatically.",
                "new_address": new_address or {},
                "note": note,
                "requires_approval": False,
            }

        if not new_address:
            return {
                "action": "change_address",
                "status": "needs_information",
                "message": "New shipping address is required before address change can be prepared.",
                "new_address": {},
                "note": note,
                "requires_approval": False,
            }

        return {
            "action": "change_address",
            "status": "needs_approval",
            "message": "Address change can be prepared but requires approval before execution.",
            "new_address": new_address,
            "note": note,
            "requires_approval": True,
        }

    def damaged_item(
        self,
        context: ShopifyOrderContext,
        *,
        reason: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        return {
            "action": "damaged_item",
            "status": "needs_approval",
            "message": "Damaged item case can be prepared for replacement or refund review.",
            "reason": reason,
            "note": note,
            "requires_approval": True,
            "eligible_actions": ["replacement", "refund", "store_credit"],
        }
