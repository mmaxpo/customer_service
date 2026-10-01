from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.domains.customer_service.models import CustomerChatWidgetSettings
from app.tenancy.models import Workspace

from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.services.ai_context_policy import (
    CustomerServiceAIContextPolicy,
)

_SPEAKERS = {"customer": "Customer", "ai": "Assistant", "agent": "Team member"}
_ORDER_REF = re.compile(r"#\s*(\d{3,20})\b")

LANGUAGES = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish", "it": "Italian",
    "nl": "Dutch", "pt": "Portuguese", "tr": "Turkish", "ar": "Arabic", "fa": "Persian",
}


def reply_language_rule(setting: dict | None, default_locale: str | None) -> str:
    """The language instruction for reply prompts, from Settings → Chat widget.
    With no setting saved, replies follow the customer's language."""
    setting = setting or {}
    default = LANGUAGES.get((default_locale or "en").split("-")[0].lower(), "English")
    if setting.get("customer_language") is False:
        return f"Write the reply in {default}, whatever language the customer writes in."
    allowed = [LANGUAGES[code] for code in setting.get("languages") or [] if code in LANGUAGES]
    if allowed:
        return (
            "Write the reply in the language of the latest customer message (the "
            "'Customer message' at the top, not the earlier messages) if it is one of: "
            f"{', '.join(allowed)}. Otherwise write the reply in {default}."
        )
    return (
        "Write the reply in the language of the latest customer message (the "
        "'Customer message' at the top, not the earlier messages): English for an "
        "English message, German for a German message, and so on."
    )


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

        widget_meta, default_locale = None, None
        if ctx.db is not None:
            widget_meta = await ctx.db.scalar(
                select(CustomerChatWidgetSettings.meta).where(
                    CustomerChatWidgetSettings.user_id == ctx.user_id
                )
            )
            default_locale = await ctx.db.scalar(
                select(Workspace.default_locale).where(Workspace.id == ctx.user_id)
            )

        return {
            "output": history,
            "patch": {
                "vars": {
                    config.save_as: history or "(no earlier messages)",
                    "conversation_order_ref": order_ref,
                    "reply_language_rule": reply_language_rule(
                        (widget_meta or {}).get("reply_language"), default_locale
                    ),
                },
            },
            "meta": {"messages": len(lines), "order_ref": order_ref},
        }
