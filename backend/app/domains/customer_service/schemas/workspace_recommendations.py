from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WorkspaceRecommendationRead(BaseModel):
    type: str
    priority: str
    reason: str
    payload: dict[str, Any] | None = None


class WorkspaceRecommendationsRead(BaseModel):
    conversation_id: UUID
    priority: str
    sla_risk: bool
    customer_risk_level: str | None = None
    customer_risk_score: int | None = None
    recommended_actions: list[WorkspaceRecommendationRead]
    automation_candidates: list[str]
    metadata: dict[str, Any]
