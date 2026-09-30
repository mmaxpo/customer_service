from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CustomerServiceWorkflowExecutionRead(BaseModel):
    job_id: UUID
    workflow_run_id: UUID | None = None
    user_id: UUID | None = None

    status: str
    job_type: str

    template_name: str | None = None
    subscription_name: str | None = None
    workflow_version: int | None = None
    handed_over: bool = False
    waiting_approval: bool = False
    trigger_event_type: str | None = None

    conversation_id: UUID | None = None
    ticket_id: UUID | None = None
    customer_id: UUID | None = None
    channel: str | None = None

    message: str | None = None
    workflow_name: str | None = None

    attempts: int
    max_attempts: int
    error_message: str | None = None

    payload: dict[str, Any]
    result: dict[str, Any] | None = None

    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CustomerServiceWorkflowTemplateRunRequest(BaseModel):
    template_id: UUID
    message: str | None = None
