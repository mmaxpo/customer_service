from __future__ import annotations

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from app.domains.customer_service.services.shopify_workflow_catalog import (
    shopify_system_workflow_templates,
)
from app.platform.jobs.service import JobService


class ShopifyActionWorkflowService:
    ACTION_TO_TEMPLATE = {
        "shopify_refund": "Shopify Refund Request Workflow",
        "shopify_cancel": "Shopify Order Cancellation Workflow",
        "shopify_damaged_item": "Shopify Damaged Item Workflow",
        "shopify_track_order": "Shopify Shipping Status Workflow",
    }

    ACTION_TO_SHOPIFY_ACTION = {
        "shopify_refund": "refund",
        "shopify_cancel": "cancel",
        "shopify_damaged_item": "damaged_item",
        "shopify_track_order": "shipping_status",
    }

    def __init__(self, db):
        self.db = db

    async def start_action_workflow(
        self,
        *,
        user_id,
        suggested_action,
        payload: dict,
    ) -> dict:
        action_type = suggested_action.action_type

        template_name = self.ACTION_TO_TEMPLATE.get(action_type)
        shopify_action = self.ACTION_TO_SHOPIFY_ACTION.get(action_type)

        if not template_name or not shopify_action:
            raise HTTPException(
                status_code=422, detail="Unsupported Shopify workflow action"
            )

        action_payload = suggested_action.payload or {}
        order_ref = payload.get("order_ref") or action_payload.get("order_ref")

        if not order_ref:
            raise HTTPException(
                status_code=422,
                detail="order_ref is required for Shopify workflow action",
            )

        workflow = self._workflow_from_template(
            template_name=template_name,
            order_ref=order_ref,
            reason=payload.get("reason") or action_payload.get("reason"),
            note=payload.get("note") or action_payload.get("note"),
            amount=payload.get("amount") or action_payload.get("amount"),
            new_address=payload.get("new_address") or payload.get("address"),
        )

        message = (
            payload.get("message")
            or f"{shopify_action} requested for order {order_ref}"
        )

        job = await JobService(self.db).enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload=jsonable_encoder(
                {
                    "workflow": workflow,
                    "message": message,
                    "thread_id": str(suggested_action.conversation_id),
                    "extras": {
                        "customer_service": True,
                        "suggested_action": {
                            "id": str(suggested_action.id),
                            "action_type": action_type,
                            "title": suggested_action.title,
                            "source": suggested_action.source,
                            "conversation_id": str(suggested_action.conversation_id),
                        },
                        "shopify_action": {
                            "action": shopify_action,
                            "order_ref": order_ref,
                            "requires_human_approval": shopify_action
                            in {"refund", "cancel", "damaged_item"},
                        },
                    },
                }
            ),
            max_attempts=3,
            idempotency_key=(
                f"cs:shopify:suggested-action:{suggested_action.id}"
            ),
        )

        return {
            "type": action_type,
            "mode": "workflow_started",
            "job_id": str(job.id),
            "job_type": job.job_type,
            "job_status": job.status,
            "order_ref": order_ref,
            "shopify_action": shopify_action,
            "requires_human_approval": shopify_action
            in {"refund", "cancel", "damaged_item"},
        }

    def _workflow_from_template(
        self,
        *,
        template_name: str,
        order_ref: str,
        reason: str | None,
        note: str | None,
        amount: str | None,
        new_address: dict | None,
    ) -> dict:
        templates = shopify_system_workflow_templates()
        template = next((t for t in templates if t["name"] == template_name), None)

        if template is None:
            raise HTTPException(
                status_code=500,
                detail=f"Shopify workflow template not found: {template_name}",
            )

        workflow = jsonable_encoder(template["workflow_json"])

        for node in workflow.get("nodes", []):
            data = node.get("data") or {}
            node_type = data.get("nodeType")

            if node.get("id") == "trigger":
                data["input"] = (
                    f"Customer requested Shopify action for order {order_ref}"
                )

            if node.get("id") == "order_ref" and node_type == "set.variable":
                data["value"] = order_ref

            if (
                node.get("id") == "shopify_action"
                and node_type == "shopify.order_action"
            ):
                data["order_ref_from"] = "vars"
                data["order_ref_key"] = "order_ref"

                if reason:
                    data["reason"] = reason
                if note:
                    data["note"] = note
                if amount:
                    data["amount"] = amount
                if new_address:
                    data["new_address"] = new_address

            if (
                node.get("id") == "shopify_action"
                and node_type == "capability.invoke"
            ):
                config = data.setdefault("config", {})
                payload = config.setdefault("payload", {})

                if reason:
                    payload["reason"] = reason
                if note:
                    payload["note"] = note
                if amount:
                    payload["amount"] = amount
                if new_address:
                    payload["new_address"] = new_address

                payload["idempotency_key"] = (
                    f"cs:shopify:cancel:{order_ref}"
                )

        return workflow
