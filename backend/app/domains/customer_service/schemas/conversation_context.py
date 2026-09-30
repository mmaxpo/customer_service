from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ConversationContextRead(BaseModel):
    conversation: dict[str, Any]
    recent_messages: list[dict[str, Any]]
    customer: dict[str, Any] | None = None
    ticket: dict[str, Any] | None = None
    tags: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    latest_insight: dict[str, Any] | None = None
    suggested_actions: list[dict[str, Any]]
    workflow_executions: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    quality_reviews: list[dict[str, Any]]
    assignments: list[dict[str, Any]]
    sla: dict[str, Any]
