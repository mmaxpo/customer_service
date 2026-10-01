from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.customer_service.repositories.chat_repository import ChatRepository
from app.domains.customer_service.services.chat_service import CustomerChatService


# A reply step's text ends with this marker when the automation promised that a
# person will follow up. The customer never sees it; the case is flagged for the team.
HANDOFF_MARKER = "[HANDOFF]"


class CustomerChatReplyConfig(BaseModel):
    node_type: Literal["reply.customer_chat"] = "reply.customer_chat"

    session_id: str | None = Field(
        default=None,
        description="Explicit customer chat session id.",
    )
    session_id_from: Literal["config", "vars", "extras"] = Field(default="extras")
    session_id_key: str = Field(default="session_id")

    message: str | None = Field(
        default=None,
        description="Explicit message to send to the customer chat.",
    )
    message_from: Literal["config", "vars", "last"] = Field(default="last")
    message_key: str = Field(default="reply")

    save_as: str = Field(default="customer_chat_reply")


class CustomerChatReplyNode:
    async def run(
        self,
        ctx,
        state: dict[str, Any],
        config: CustomerChatReplyConfig,
    ) -> dict[str, Any]:
        if ctx.db is None:
            raise ValueError("reply.customer_chat requires ctx.db")

        vars_ = state.get("vars") or {}
        extras = getattr(ctx, "extras", None) or {}

        if config.session_id_from == "config":
            raw_session_id = config.session_id
        elif config.session_id_from == "vars":
            raw_session_id = vars_.get(config.session_id_key)
        else:
            event = extras.get("event") or {}
            event_payload = event.get("payload") if isinstance(event, dict) else {}
            raw_session_id = (
                event_payload.get(config.session_id_key)
                if isinstance(event_payload, dict)
                else None
            ) or extras.get(config.session_id_key)

        raw_session_id = str(raw_session_id or "").strip()
        if not raw_session_id:
            raise ValueError("reply.customer_chat requires a session_id")

        if config.message_from == "config":
            message = config.message
        elif config.message_from == "vars":
            message = vars_.get(config.message_key)
        else:
            message = state.get("last")

        message = str(message or "").strip()
        if not message:
            message = _fallback_customer_chat_message(state)

        handoff_required = HANDOFF_MARKER in message
        message = message.replace(HANDOFF_MARKER, "").strip()

        if not message:
            raise ValueError("reply.customer_chat requires a non-empty message")

        idempotency_key = (
            (getattr(ctx, "node_data", None) or {}).get("_runtime") or {}
        ).get("idempotency_key")

        service = CustomerChatService(ChatRepository(ctx.db))

        session = await service.get_session(
            session_id=UUID(raw_session_id),
        )
        if session is None:
            raise ValueError("reply.customer_chat session not found")

        if str(session.user_id) != str(ctx.user_id):
            raise PermissionError(
                "reply.customer_chat session does not belong to current user"
            )

        chat_message = await service.add_ai_message(
            session_id=session.id,
            content=message,
            client_message_id=idempotency_key,
        )

        inbox_message = await service.add_inbox_ai_message_for_chat_session(
            session=session,
            chat_message=chat_message,
        )

        output = {
            "chat_message_id": str(chat_message.id),
            "session_id": str(session.id),
            "conversation_id": (
                str(inbox_message.conversation_id)
                if inbox_message is not None
                else None
            ),
            "inbox_message_id": (
                str(inbox_message.id) if inbox_message is not None else None
            ),
            "role": chat_message.role,
            "content": chat_message.content,
            "idempotency_key": idempotency_key,
        }

        return {
            "output": output,
            "patch": {
                "vars": {
                    config.save_as: output,
                    "customer_chat_reply_sent": True,
                },
                "last": output,
            },
            "meta": {
                "session_id": str(session.id),
                "chat_message_id": str(chat_message.id),
                "inbox_message_id": output["inbox_message_id"],
                "idempotency_key": idempotency_key,
                **({"handoff_required": True} if handoff_required else {}),
            },
        }


def _fallback_customer_chat_message(state: dict[str, Any]) -> str:
    vars_ = state.get("vars") or {}
    order = vars_.get("shopify_order") or {}
    summary = order.get("summary") if isinstance(order, dict) else None

    if isinstance(summary, dict):
        order_name = summary.get("order_name") or vars_.get("order_ref") or "your order"

        if summary.get("found") is False:
            note = str(summary.get("customer_safe_note") or "").strip()

            if note:
                return note

            return (
                f"I couldn't find order {order_name}. "
                "Please check the order number and try again."
            )

        total = summary.get("total_price")
        currency = summary.get("currency") or ""
        fulfillment = summary.get("fulfillment_status") or "unknown"
        note = summary.get("customer_safe_note")

        parts = [f"I found {order_name}. Its fulfillment status is {fulfillment}."]
        if total:
            parts.append(f"Total: {total} {currency}".strip())
        if note:
            parts.append(str(note))
        actions = summary.get("available_actions") or {}
        if actions:
            parts.append("Available support actions may require human review.")
        return " ".join(parts).strip()

    text = str(vars_.get("input") or state.get("last") or "").strip()
    if text:
        return "Thanks for your message. A support agent can review this and help you shortly."

    return ""
