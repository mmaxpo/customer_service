from __future__ import annotations

from typing import Any

from app.domains.customer_service.schemas.shopify_order_context import (
    ShopifyOrderContext,
)
from app.domains.customer_service.services.shopify_workflow_decisions import (
    ShopifySupportWorkflowDecisionService,
)


class ShopifySupportWorkflowOrchestrator:
    def __init__(
        self,
        decision_service: ShopifySupportWorkflowDecisionService | None = None,
    ):
        self.decisions = decision_service or ShopifySupportWorkflowDecisionService()

    def handle(
        self,
        *,
        workflow_type: str,
        order_context: ShopifyOrderContext,
        reason: str | None = None,
        note: str | None = None,
        new_address: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workflow_type = self._normalize_workflow_type(workflow_type)

        decision = self._decision(
            workflow_type=workflow_type,
            order_context=order_context,
            reason=reason,
            note=note,
            new_address=new_address,
        )

        return {
            "workflow_type": workflow_type,
            "order": {
                "order_id": order_context.order_id,
                "order_name": order_context.order_name,
                "customer_email": order_context.customer_email,
                "financial_status": order_context.financial_status,
                "fulfillment_status": order_context.fulfillment_status,
            },
            "decision": decision,
            "next_action": self._next_action(decision),
            "requires_approval": bool(decision.get("requires_approval")),
        }

    def _decision(
        self,
        *,
        workflow_type: str,
        order_context: ShopifyOrderContext,
        reason: str | None,
        note: str | None,
        new_address: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if workflow_type == "shipping_status":
            return self.decisions.shipping_status(order_context)

        if workflow_type == "refund":
            return self.decisions.refund(order_context, reason=reason)

        if workflow_type == "cancel":
            return self.decisions.cancel(order_context, reason=reason)

        if workflow_type == "change_address":
            return self.decisions.change_address(
                order_context,
                new_address=new_address,
                note=note,
            )

        if workflow_type == "damaged_item":
            return self.decisions.damaged_item(
                order_context,
                reason=reason,
                note=note,
            )

        return {
            "action": workflow_type,
            "status": "unsupported",
            "message": f"Unsupported Shopify support workflow: {workflow_type}",
            "requires_approval": False,
        }

    def _next_action(self, decision: dict[str, Any]) -> str:
        status = decision.get("status")

        if status == "ready":
            return "reply_ready"

        if status == "needs_approval":
            return "approval_required"

        if status == "needs_information":
            return "request_more_information"

        if status == "blocked":
            return "blocked"

        return "manual_review"

    def _normalize_workflow_type(self, value: str) -> str:
        normalized = (value or "").strip().lower()

        aliases = {
            "track_order": "shipping_status",
            "tracking": "shipping_status",
            "shipping": "shipping_status",
            "order_status": "shipping_status",
            "refund_request": "refund",
            "cancellation": "cancel",
            "cancel_order": "cancel",
            "address_change": "change_address",
            "damaged": "damaged_item",
            "damaged_product": "damaged_item",
        }

        return aliases.get(normalized, normalized)
