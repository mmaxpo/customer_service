from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerServiceKnowledgeSearchRequest(BaseModel):
    query: str
    k: int = 5


class CustomerServiceKnowledgeHit(BaseModel):
    doc_id: str | None = None
    title: str | None = None
    filename: str | None = None
    content: str
    score: float | None = None
    source: str | None = None
    page: int | None = None
    chunk_index: int | None = None


class CustomerServiceKnowledgeContext(BaseModel):
    query: str
    context: str
    hits: list[CustomerServiceKnowledgeHit]
    answered: bool = True
    no_answer_policy: str | None = None
    no_answer_message: str | None = None
    citations: list[dict] = Field(default_factory=list)


class KnowledgeURLIngestRequest(BaseModel):
    url: str
    name: str | None = None
    max_pages: int = Field(default=10, ge=1, le=25)


class KnowledgeInlineIngestRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)


class KnowledgeSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    kind: str
    name: str
    source_uri: str | None
    external_id: str | None
    status: str
    freshness_status: str
    error: str | None
    meta: dict
    last_checked_at: datetime | None
    last_indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KnowledgeSettingsUpdate(BaseModel):
    no_answer_policy: Literal["handoff", "clarify", "draft_only"] = "handoff"
    no_answer_message: str = Field(min_length=1, max_length=1000)
    minimum_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    freshness_days: int = Field(default=30, ge=1, le=365)
    citations_required: bool = True


class KnowledgeSettingsRead(KnowledgeSettingsUpdate):
    workspace_id: UUID
    updated_at: datetime


class KnowledgeEvaluationQuestionCreate(BaseModel):
    question: str = Field(min_length=1)
    expected_answer: str | None = None
    tags: list[str] = Field(default_factory=list)


class KnowledgeEvaluationQuestionRead(KnowledgeEvaluationQuestionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    is_active: bool
    created_at: datetime
