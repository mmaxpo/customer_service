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

        refusal = _chat_order_refusal(ctx, vars_, output, order_ref)

        if refusal:
            output = _unverified_order(order_ref, refusal)

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
                "email_verified": refusal is None,
                # No email on the order: only a person can confirm who owns it.
                **({"handoff_required": True} if refusal and "team member" in refusal else {}),
            },
        }


def _chat_order_refusal(
    ctx, vars_: dict[str, Any], output: dict[str, Any], order_ref: str
) -> str | None:
    """In a customer chat, share an order only with the email it was placed with:
    the email the chat started with, or one the customer typed in this conversation.
    Returns what to tell the customer when the order can't be shared."""
    event_payload = ((getattr(ctx, "extras", None) or {}).get("event") or {}).get(
        "payload"
    ) or {}

    if not event_payload.get("session_id") or not output.get("order_id"):
        return None

    order_email = str(output.get("customer_email") or "").strip().lower()

    if not order_email:
        return (
            f"I can't confirm automatically that order {order_ref} belongs to you. "
            "A team member will check and reply here."
        )

    chat_email = str(event_payload.get("customer_email") or "").strip().lower()

    typed = f"{vars_.get('input') or ''}\n{vars_.get('conversation') or ''}".lower()

    if chat_email == order_email or order_email in typed:
        return None

    return (
        f"To protect your order details, I can only share order {order_ref} "
        "with the email address it was placed with. Please reply with the "
        "order number and that email address."
    )


def _unverified_order(order_ref: str, note: str) -> dict[str, Any]:
    return {
        "found": False,
        "order_ref": order_ref,
        "order_name": None,
        "order_id": None,
        "customer_email": None,
        "context": None,
        "payload": None,
        "summary": {
            "found": False,
            "order_ref": order_ref,
            "order_name": order_ref,
            "available_actions": {},
            "customer_safe_note": note,
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
