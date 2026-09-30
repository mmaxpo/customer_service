from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.runtime.resources import get_runtime_services


class ShopifyGetOrderConfig(BaseModel):
    node_type: Literal["shopify.get_order"] = "shopify.get_order"

    order_ref: str | None = Field(
        default=None,
        description="Explicit Shopify order reference, for example #10482",
    )
    order_ref_from: Literal["config", "vars", "last"] = Field(default="vars")
    order_ref_key: str = Field(default="order_ref")

    save_as: str = Field(default="shopify_order")


class ShopifyGetOrderNode:
    async def run(
        self, ctx, state: dict[str, Any], config: ShopifyGetOrderConfig
    ) -> dict[str, Any]:
        services = get_runtime_services(ctx)
        capabilities = services.capabilities

        if capabilities is None:
            raise ValueError("shopify.get_order requires runtime capability invoker")

        vars_ = state.get("vars") or {}

        if config.order_ref_from == "config":
            order_ref = config.order_ref
        elif config.order_ref_from == "last":
            order_ref = state.get("last")
        else:
            order_ref = vars_.get(config.order_ref_key)

        order_ref = str(order_ref or "").strip()
        if not order_ref:
            raise ValueError("shopify.get_order requires an order_ref")

        output = await capabilities.invoke(
            "shopify.get_order",
            user_id=getattr(ctx, "user_id", None),
            payload={
                "order_ref": order_ref,
            },
        )

        return {
            "output": output,
            "patch": {
                "vars": {
                    config.save_as: output,
                    "order_ref": order_ref,
                },
                "last": output,
            },
            "meta": {
                "order_ref": order_ref,
                "order_id": output.get("order_id"),
                "order_name": output.get("order_name"),
            },
        }


class ShopifyOrderActionConfig(BaseModel):
    node_type: Literal["shopify.order_action"] = "shopify.order_action"

    action: Literal[
        "refund",
        "cancel",
        "change_address",
        "damaged_item",
        "shipping_status",
        "reship",
    ]

    order_ref: str | None = None
    order_ref_from: Literal["config", "vars", "last"] = Field(default="vars")
    order_ref_key: str = Field(default="order_ref")

    reason: str | None = None
    note: str | None = None
    amount: str | None = None
    new_address: dict[str, Any] | None = None
    scope: dict[str, Any] | None = None

    save_as: str = Field(default="shopify_action")


class ShopifyOrderActionNode:
    async def run(
        self, ctx, state: dict[str, Any], config: ShopifyOrderActionConfig
    ) -> dict[str, Any]:
        services = get_runtime_services(ctx)
        shopify = services.business.shopify

        if shopify is None:
            raise ValueError("shopify.order_action requires runtime shopify service")

        vars_ = state.get("vars") or {}

        if config.order_ref_from == "config":
            order_ref = config.order_ref
        elif config.order_ref_from == "last":
            last = state.get("last")
            order_ref = last.get("order_name") if isinstance(last, dict) else last
        else:
            order_ref = vars_.get(config.order_ref_key)

        order_ref = str(order_ref or "").strip()
        if not order_ref:
            raise ValueError("shopify.order_action requires an order_ref")

        idempotency_key = (
            (getattr(ctx, "node_data", None) or {}).get("_runtime") or {}
        ).get("idempotency_key")

        resume_input = vars_.get("resume_input") or {}
        workflow_run_id = (
            state.get("run_id")
            or state.get("workflow_run_id")
            or (state.get("meta") or {}).get("workflow_run_id")
            or getattr(ctx, "thread_id", None)
        )

        output = await shopify.perform_order_action(
            user_id=ctx.user_id,
            action=config.action,
            order_ref=order_ref,
            reason=config.reason,
            note=config.note,
            new_address=config.new_address,
            amount=config.amount,
            scope=config.scope,
            idempotency_key=idempotency_key,
            approval_wait_id=resume_input.get("wait_id"),
            workflow_run_id=str(workflow_run_id) if workflow_run_id else None,
        )

        return {
            "output": output,
            "patch": {
                "vars": {
                    config.save_as: output,
                    "shopify_action_status": output.get("status"),
                },
                "last": output,
            },
            "meta": {
                "action": config.action,
                "order_ref": order_ref,
                "status": output.get("status"),
                "order_id": output.get("order_id"),
                "idempotency_key": idempotency_key,
            },
        }
