from __future__ import annotations

from pydantic import BaseModel


class ReplyQualityDashboardItem(BaseModel):
    key: str
    total: int
    acceptance_rate: float
    edit_rate: float
    rejection_rate: float
    average_score: float | None = None


class ReplyQualityDashboardRead(BaseModel):
    best_reply_types: list[ReplyQualityDashboardItem]
    worst_reply_types: list[ReplyQualityDashboardItem]

    best_intents: list[ReplyQualityDashboardItem]
    worst_intents: list[ReplyQualityDashboardItem]

    high_edit_reply_types: list[ReplyQualityDashboardItem]
    high_rejection_intents: list[ReplyQualityDashboardItem]
