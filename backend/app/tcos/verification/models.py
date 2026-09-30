from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class VerificationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class VerificationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: VerificationSeverity
    message: str
    location: str | None = None
    details: dict = Field(default_factory=dict)


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    issues: list[VerificationIssue] = Field(default_factory=list)
    confidence: dict = Field(default_factory=dict)
