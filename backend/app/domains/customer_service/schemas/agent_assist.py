from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReplySuggestionResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    suggestion: str
    source: str
    intent: str | None = None
    confidence: float | None = None
    workflow_run_id: UUID | None = None
    status: str
    created_at: datetime


class AgentAssistSuggestionRead(BaseModel):
    id: UUID
    conversation_id: UUID
    source_message_id: UUID | None = None
    workflow_run_id: UUID | None = None
    intent: str | None = None
    confidence: float | None = None
    original_suggestion: str
    current_suggestion: str
    status: str
    reviewed_by: UUID | None = None
    approved_by: UUID | None = None
    sent_message_id: UUID | None = None
    meta: dict | None = None
    created_at: datetime
    updated_at: datetime


class AgentAssistSuggestionRevisionRead(BaseModel):
    id: UUID
    suggestion_id: UUID
    revision_number: int
    body: str
    edited_by: UUID | None = None
    change_reason: str | None = None
    meta: dict | None = None
    created_at: datetime


class AgentAssistSuggestionUpdate(BaseModel):
    current_suggestion: str = Field(min_length=1)
    change_reason: str | None = None
