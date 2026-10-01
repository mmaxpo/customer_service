from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.services.ai_context_policy import (
    CustomerServiceAIContextPolicy,
)

_SPEAKERS = {"customer": "Customer", "ai": "Assistant", "agent": "Team member"}
_ORDER_REF = re.compile(r"#\s*(\d{3,20})\b")


class LoadConversationConfig(BaseModel):
    node_type: Literal["customer_service.load_conversation"] = (
        "customer_service.load_conversation"
    )

    save_as: str = Field(
        default="conversation",
        description="vars key for the earlier messages of this conversation, as text.",
    )


class LoadConversationNode:
    """
    Gives later steps the memory of this conversation: the recent earlier
    messages (bounded by the AI context policy) and the last order number the
    customer mentioned.
    """

    async def run(
        self,
        ctx,
        state: dict[str, Any],
        config: LoadConversationConfig,
    ) -> dict[str, Any]:
        extras = getattr(ctx, "extras", None) or {}
        event_payload = (extras.get("event") or {}).get("payload") or {}
        conversation_id = event_payload.get("conversation_id")

        messages = []
        if conversation_id and ctx.db is not None:
            policy = CustomerServiceAIContextPolicy.from_env()
            messages = (
                await ConversationRepository(ctx.db).list_recent_context_messages(
                    user_id=ctx.user_id,
                    conversation_id=UUID(str(conversation_id)),
                    limit=policy.recent_message_limit,
                )
                or []
            )

        current = str((state.get("vars") or {}).get("input") or "").strip()
        # The message being answered is already saved; it is not "earlier".
        if (
            messages
            and str(messages[-1].sender_type).lower().endswith("customer")
            and (messages[-1].body or "").strip() == current
        ):
            messages = messages[:-1]

        lines = []
        order_ref = ""
        for message in messages:
            sender = str(getattr(message.sender_type, "value", message.sender_type)).lower()
            speaker = _SPEAKERS.get(sender)
            body = (message.body or "").strip()
            if not speaker or not body:
                continue
            lines.append(f"{speaker}: {body}")
            if sender == "customer":
                found = _ORDER_REF.findall(body)
                if found:
                    order_ref = f"#{found[-1]}"

        history = "\n".join(lines)
        if conversation_id and lines:
            history = CustomerServiceAIContextPolicy.from_env().trim_text(history)

        return {
            "output": history,
            "patch": {
                "vars": {
                    config.save_as: history or "(no earlier messages)",
                    "conversation_order_ref": order_ref,
                },
            },
            "meta": {"messages": len(lines), "order_ref": order_ref},
        }
