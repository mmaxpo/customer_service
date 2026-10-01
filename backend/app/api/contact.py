"""Public contact form: forwards a visitor's message to the Tajeran team."""

from __future__ import annotations

import hashlib
import html
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.http_safety import RateLimitStore
from app.services.email_service import EmailType, send_email

router = APIRouter(prefix="/contact", tags=["contact"])

CONTACT_RATE_WINDOW_SECONDS = 600
CONTACT_LIMIT_PER_WINDOW = 5
_contact_rate_store = RateLimitStore(settings.REDIS_URL)

CONTACT_INBOX = {
    "sales": "sales@tajeran.ai",
    "support": "support@tajeran.ai",
}


class ContactMessage(BaseModel):
    topic: Literal["sales", "support"]
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)


@router.post("", status_code=202)
async def send_contact_message(data: ContactMessage, request: Request) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"
    ip_digest = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:24]
    try:
        count = await _contact_rate_store.increment(
            f"contact:ip:{ip_digest}",
            window_seconds=CONTACT_RATE_WINDOW_SECONDS,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None
    if count > CONTACT_LIMIT_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail="Too many messages. Please try again later.",
            headers={"Retry-After": str(CONTACT_RATE_WINDOW_SECONDS)},
        )

    name = " ".join(data.name.split())
    body = html.escape(data.message).replace("\n", "<br>")
    try:
        await run_in_threadpool(
            send_email,
            email_type=EmailType.NOTIFICATION,
            to=CONTACT_INBOX[data.topic],
            subject=f"Contact form ({data.topic}): {name}",
            html=f"<p>From {html.escape(name)} &lt;{html.escape(str(data.email))}&gt;</p><p>{body}</p>",
            reply_to=str(data.email),
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="We could not send your message. Please email us instead.",
        ) from None

    return {"detail": "Message sent."}
