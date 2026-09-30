from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


AutomationActivityCategory = Literal[
    "conversation",
    "ai_decision",
    "workflow_execution",
    "provider_call",
    "approval",
    "failure_retry",
    "verification",
    "repair",
    "learned_insight",
]


class AutomationActivityEventRead(BaseModel):
    id: str
    category: AutomationActivityCategory
    type: str
    timestamp: datetime
    title: str
    description: str | None = None
    status: str | None = None
    actor_id: str | None = None
    workflow_run_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict[str, Any]


class AutomationActivityRead(BaseModel):
    conversation_id: str
    items: list[AutomationActivityEventRead]
    counts: dict[str, int]
    has_more: bool

