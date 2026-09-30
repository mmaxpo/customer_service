from __future__ import annotations

import time
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class LearningEpisodeStatus(StrEnum):
    CREATED = "created"
    ANALYZED = "analyzed"


class LearningEpisode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    status: LearningEpisodeStatus = LearningEpisodeStatus.CREATED
    planner_session_id: str
    goal: str
    selected_candidate: dict[str, Any] | None = None
    business_plan: dict[str, Any] | None = None
    compilation: dict[str, Any] | None = None
    verification_result: dict[str, Any] | None = None
    repair_result: dict[str, Any] | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at_ts: float = Field(default_factory=time.time)


class LearningInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(default_factory=dict)


class LearningResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode: LearningEpisode
    insights: list[LearningInsight] = Field(default_factory=list)
