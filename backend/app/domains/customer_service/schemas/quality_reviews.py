from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class QualityReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    conversation_id: UUID

    overall_score: float

    scores: dict | None = None

    issues: list | None = None

    recommendations: list | None = None

    reviewer_type: str

    created_at: datetime
