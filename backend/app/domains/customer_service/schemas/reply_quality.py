from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReplyQualityCreate(BaseModel):
    conversation_id: UUID
    reply_message_id: UUID | None = None

    outcome: str = Field(
        ..., pattern="^(accepted_without_edit|accepted_with_edit|rejected)$"
    )

    score: float | None = Field(default=None, ge=0, le=5)
    accuracy_score: float | None = Field(default=None, ge=0, le=5)
    relevance_score: float | None = Field(default=None, ge=0, le=5)
    tone_score: float | None = Field(default=None, ge=0, le=5)

    draft_body: str | None = None
    final_body: str | None = None


class ReplyQualityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    conversation_id: UUID
    reply_message_id: UUID | None = None

    review_type: str
    outcome: str | None = None

    overall_score: float
    accuracy_score: float | None = None
    relevance_score: float | None = None
    tone_score: float | None = None

    draft_body: str | None = None
    final_body: str | None = None
    edit_distance: int | None = None
    reviewer_id: UUID | None = None
    created_at: datetime


class ReplyQualityAnalyticsRead(BaseModel):
    total_reviews: int
    accepted_without_edit: int
    accepted_with_edit: int
    rejected: int
    average_score: float | None = None
    average_accuracy_score: float | None = None
    average_relevance_score: float | None = None
    average_tone_score: float | None = None
