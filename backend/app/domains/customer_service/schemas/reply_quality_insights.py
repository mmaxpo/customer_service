from __future__ import annotations

from pydantic import BaseModel


class ReplyQualityBucketRead(BaseModel):
    key: str
    total: int
    accepted_without_edit: int
    accepted_with_edit: int
    rejected: int
    acceptance_rate: float
    edit_rate: float
    rejection_rate: float
    average_score: float | None = None


class ReplyQualityInsightsRead(BaseModel):
    total_reviews: int
    accepted_without_edit: int
    accepted_with_edit: int
    rejected: int

    acceptance_rate: float
    edit_rate: float
    rejection_rate: float

    average_score: float | None = None
    average_edit_distance: float | None = None

    by_reply_type: list[ReplyQualityBucketRead]
    by_intent: list[ReplyQualityBucketRead]
