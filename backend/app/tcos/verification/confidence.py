from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.tcos.verification.models import VerificationResult, VerificationSeverity


class VerificationConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall: float = Field(ge=0.0, le=1.0)
    issue_penalty: float = Field(ge=0.0, le=1.0)
    error_count: int
    warning_count: int


def calculate_verification_confidence(
    result: VerificationResult,
) -> VerificationConfidence:
    error_count = sum(
        1 for issue in result.issues if issue.severity == VerificationSeverity.ERROR
    )
    warning_count = sum(
        1 for issue in result.issues if issue.severity == VerificationSeverity.WARNING
    )

    penalty = min(1.0, (error_count * 0.5) + (warning_count * 0.1))
    overall = max(0.0, 1.0 - penalty)

    return VerificationConfidence(
        overall=overall,
        issue_penalty=penalty,
        error_count=error_count,
        warning_count=warning_count,
    )
