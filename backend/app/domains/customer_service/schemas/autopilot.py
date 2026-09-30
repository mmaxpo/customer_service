from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


AutopilotMode = Literal[
    "recommend_only",
    "draft_reply",
    "auto_send_safe",
    "require_approval",
    "never_automate",
]
ActionKind = Literal["reply", "mutation", "routing", "internal"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class AutopilotPolicyWrite(BaseModel):
    intent: str = Field(min_length=1, max_length=100)
    mode: AutopilotMode = "draft_reply"
    minimum_confidence: float = Field(default=0.85, ge=0, le=1)
    maximum_auto_risk: RiskLevel = "low"
    allowed_channels: list[str] = Field(
        default_factory=lambda: ["email", "website_chat"], max_length=20
    )
    allowed_languages: list[str] = Field(default_factory=lambda: ["*"], max_length=50)
    mutation_requires_approval: bool = True
    is_enabled: bool = True

    @field_validator("intent")
    @classmethod
    def normalize_intent(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    @field_validator("allowed_channels", "allowed_languages")
    @classmethod
    def normalize_values(cls, value: list[str]) -> list[str]:
        normalized = [item.strip().lower() for item in value if item.strip()]
        if not normalized:
            raise ValueError("At least one value is required")
        return list(dict.fromkeys(normalized))


class AutopilotPolicyRead(AutopilotPolicyWrite):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AutopilotEvaluationRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=100)
    action_kind: ActionKind
    risk: RiskLevel = "low"
    confidence: float = Field(ge=0, le=1)
    channel: str = Field(min_length=1, max_length=50)
    language: str = Field(default="und", min_length=2, max_length=16)
    action_type: str | None = Field(default=None, max_length=100)

    @field_validator("channel")
    @classmethod
    def canonical_channel(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"chat", "web", "website"}:
            return "website_chat"
        return normalized

    @field_validator("intent", "language")
    @classmethod
    def normalize_evaluation_value(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "_")


class AutopilotDecisionRead(BaseModel):
    policy_id: UUID | None = None
    matched_intent: str
    requested_mode: AutopilotMode
    decision: AutopilotMode
    may_send: bool
    may_execute: bool
    requires_approval: bool
    reason_codes: list[str]
    confidence: float
    risk: RiskLevel
    action_kind: ActionKind
    channel: str
    language: str


class ConversationAutopilotDecisionRequest(BaseModel):
    action_kind: ActionKind = "reply"
    risk: RiskLevel = "low"
    channel: str | None = Field(default=None, max_length=50)
    action_type: str | None = Field(default=None, max_length=100)
    force_refresh_intelligence: bool = False
