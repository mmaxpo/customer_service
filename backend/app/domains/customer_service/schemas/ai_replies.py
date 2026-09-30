from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AIReplyComposeRequest(BaseModel):
    customer_message: str | None = None
    shopify_context: dict[str, Any] | None = None
    force_refresh_intelligence: bool = False


class AIReplyComposeRead(BaseModel):
    body: str
    confidence: float
    reply_type: str
    requires_review: bool
    source_summary: dict[str, Any]
    sources: dict[str, Any]
