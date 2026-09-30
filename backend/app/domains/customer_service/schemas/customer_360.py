from typing import Any

from pydantic import BaseModel


class Customer360Read(BaseModel):
    customer: dict[str, Any]
    summary: dict[str, Any]
    recent_conversations: list[dict[str, Any]]
    recent_tickets: list[dict[str, Any]]
    recent_activity: list[dict[str, Any]]
    workflow_executions: list[dict[str, Any]]
    tags: list[str]
