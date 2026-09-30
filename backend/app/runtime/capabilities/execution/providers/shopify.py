from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.runtime.capabilities.execution.contracts import (
    CapabilityExecutionContext,
)
from app.runtime.capabilities.execution.registry import (
    CapabilityExecutorRegistry,
)


def _require_shopify_service(
    context: CapabilityExecutionContext,
) -> Any:
    shopify = getattr(
        getattr(context.services, "business", None),
        "shopify",
        None,
    )

    if shopify is None:
        raise ValueError(
            f"Capability {context.invocation.capability_id} "
            "requires services.business.shopify"
        )

    return shopify


def _resolve_user_id(
    context: CapabilityExecutionContext,
) -> Any:
    user_id = context.invocation.user_id or getattr(
        getattr(context.services, "identity", None),
        "user_id",
        None,
    )

    if user_id is None:
        raise ValueError(
            f"Capability {context.invocation.capability_id} requires user_id"
        )

    return user_id


async def execute_shopify_get_order(
    context: CapabilityExecutionContext,
) -> Any:
    shopify = _require_shopify_service(context)
    user_id = _resolve_user_id(context)

    order_ref = str(context.invocation.inputs.get("order_ref") or "").strip()

    if not order_ref:
        raise ValueError(
            f"Capability {context.invocation.capability_id} requires payload.order_ref"
        )

    try:
        kwargs = {"user_id": user_id, "order_ref": order_ref}
        connection_id = context.invocation.inputs.get("connection_id")
        if connection_id is not None:
            kwargs["connection_id"] = connection_id
        return await shopify.get_order(**kwargs)
    except HTTPException as exc:
        detail = str(exc.detail or "").strip()

        if not (exc.status_code == 404 and "order" in detail.lower()):
            raise

        customer_safe_message = (
            f"I couldn't find order {order_ref}. "
            "Please check the order number and try again."
        )

        # Order-not-found is a normal business result. It must not cause the
        # workflow job to retry or enter dead-letter.
        return {
            "found": False,
            "order_ref": order_ref,
            "order_id": None,
            "order_name": None,
            "customer_email": None,
            "payload": None,
            "context": None,
            "summary": {
                "found": False,
                "order_ref": order_ref,
                "order_name": order_ref,
                "customer_safe_note": customer_safe_message,
                "available_actions": {},
            },
        }


async def execute_shopify_order_action(
    context: CapabilityExecutionContext,
) -> Any:
    shopify = _require_shopify_service(context)
    user_id = _resolve_user_id(context)
    payload = context.invocation.inputs

    return await shopify.perform_order_action(
        user_id=user_id,
        connection_id=payload.get("connection_id"),
        action=payload["action"],
        order_ref=payload["order_ref"],
        reason=payload.get("reason"),
        note=payload.get("note"),
        new_address=payload.get("new_address"),
        amount=payload.get("amount"),
        scope=payload.get("scope"),
        idempotency_key=payload.get("idempotency_key"),
    )


async def execute_shopify_get_order_tracking(
    context: CapabilityExecutionContext,
) -> Any:
    shopify = _require_shopify_service(context)
    user_id = _resolve_user_id(context)

    order_ref = str(context.invocation.inputs.get("order_ref") or "").strip()

    if not order_ref:
        raise ValueError(
            f"Capability {context.invocation.capability_id} requires payload.order_ref"
        )

    return await shopify.perform_order_action(
        user_id=user_id,
        connection_id=context.invocation.inputs.get("connection_id"),
        action="shipping_status",
        order_ref=order_ref,
        idempotency_key=context.invocation.inputs.get("idempotency_key"),
    )


async def execute_shopify_add_order_note(
    context: CapabilityExecutionContext,
) -> Any:
    shopify = _require_shopify_service(context)
    user_id = _resolve_user_id(context)

    order_ref = str(context.invocation.inputs.get("order_ref") or "").strip()
    note = str(context.invocation.inputs.get("note") or "").strip()

    if not order_ref:
        raise ValueError(
            f"Capability {context.invocation.capability_id} requires payload.order_ref"
        )
    if not note:
        raise ValueError(
            f"Capability {context.invocation.capability_id} requires payload.note"
        )

    return await shopify.perform_order_action(
        user_id=user_id,
        connection_id=context.invocation.inputs.get("connection_id"),
        action="add_note",
        order_ref=order_ref,
        note=note,
        idempotency_key=context.invocation.inputs.get("idempotency_key"),
    )


def register_shopify_executors(
    registry: CapabilityExecutorRegistry,
) -> None:
    registry.register(
        "shopify.get_order",
        execute_shopify_get_order,
    )
    registry.register(
        "shopify.order_action",
        execute_shopify_order_action,
    )
    registry.register(
        "shopify.get_order_tracking",
        execute_shopify_get_order_tracking,
    )
    registry.register(
        "shopify.add_order_note",
        execute_shopify_add_order_note,
    )


__all__ = [
    "execute_shopify_get_order",
    "execute_shopify_order_action",
    "execute_shopify_get_order_tracking",
    "execute_shopify_add_order_note",
    "register_shopify_executors",
]
