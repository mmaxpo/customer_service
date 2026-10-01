"""
Chat widget self-service: the buttons a customer sees when the chat opens.
"Track my order" answers straight from Shopify (no AI); "Report a problem"
and "Start a return" hand the request to the team (no automation runs).
"""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.http_safety import RateLimitStore
from app.domains.customer_service.services.chat_service import CustomerChatService
from app.runtime_services import build_application_runtime_services

RequestKind = Literal["report_problem", "start_return"]

REQUEST_TITLES: dict[str, str] = {
    "report_problem": "Report a problem",
    "start_return": "Start a return",
}
HANDED_TO_TEAM_REPLY = (
    "Thanks. I've passed your request to our team. They'll review it "
    "and reply here. Nothing on your order has been changed yet."
)

# Order lookups are public, so guessing order numbers or emails is limited.
TRACK_ORDER_WINDOW_SECONDS = 600
TRACK_ORDER_LIMIT_PER_WINDOW = 10
_track_order_rate = RateLimitStore(app_settings.REDIS_URL)

_LOGO_DATA_URL = re.compile(r"data:image/(png|jpeg|webp);base64,")


def enabled_self_service(widget_settings) -> dict[str, bool]:
    """Which self-service buttons the merchant switched on (Settings → Chat widget)."""
    chosen = (widget_settings.meta or {}).get("self_service") or {}
    return {key: bool(chosen.get(key)) for key in ("track_order", *REQUEST_TITLES)}


def widget_logo(widget_settings) -> str | None:
    """The merchant's logo (an uploaded image stored as a data URL), if any."""
    logo = (widget_settings.meta or {}).get("logo")
    return logo if isinstance(logo, str) and _LOGO_DATA_URL.match(logo) else None


def order_ref(order_number: str) -> str:
    return "#" + order_number.strip().lstrip("#").strip()


class ChatSelfService:
    def __init__(self, db: AsyncSession, chat: CustomerChatService):
        self.db = db
        self.chat = chat

    async def track_order(self, *, session, order_number: str, email: str) -> dict:
        """Order status, shared only when the order number and the email it was
        placed with both match. A wrong number and a wrong email get the same answer."""
        attempts = await _track_order_rate.increment(
            f"track-order:{session.id}", window_seconds=TRACK_ORDER_WINDOW_SECONDS
        )
        if attempts > TRACK_ORDER_LIMIT_PER_WINDOW:
            raise HTTPException(
                status_code=429,
                detail="Too many order lookups. Please try again later.",
                headers={"Retry-After": str(TRACK_ORDER_WINDOW_SECONDS)},
            )

        order = await build_application_runtime_services(
            db=self.db, user_id=session.user_id
        ).capabilities.invoke(
            "shopify.get_order",
            user_id=session.user_id,
            payload={"order_ref": order_ref(order_number)},
        )

        order_email = str(order.get("customer_email") or "").strip().lower()
        if not order.get("order_id") or not order_email or order_email != email.strip().lower():
            return {"found": False}

        summary = order.get("summary") or {}
        return {
            "found": True,
            "order_name": order.get("order_name"),
            "paid": bool(summary.get("is_paid")),
            "shipped": bool(summary.get("is_fulfilled")),
            "carrier": summary.get("carrier"),
            "tracking_number": summary.get("tracking_number"),
            "tracking_url": summary.get("tracking_url"),
        }

    async def submit_request(
        self, *, session, kind: RequestKind, order_number: str, description: str
    ) -> UUID | None:
        """Save the request as a customer message plus a "passed to our team"
        reply. Returns the inbox conversation id, if the chat is linked to one."""
        message = await self.chat.add_customer_message(
            session_id=session.id,
            content=f"{REQUEST_TITLES[kind]}: order {order_ref(order_number)}\n{description.strip()}",
        )
        inbox_message = await self.chat.add_inbox_customer_message_for_chat_session(
            session=session, chat_message=message
        )
        reply = await self.chat.add_ai_message(session_id=session.id, content=HANDED_TO_TEAM_REPLY)
        await self.chat.add_inbox_ai_message_for_chat_session(session=session, chat_message=reply)
        await self.chat.commit()
        return inbox_message.conversation_id if inbox_message is not None else None
