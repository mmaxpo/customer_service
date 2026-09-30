from __future__ import annotations

from collections.abc import Callable

from app.tcos.planner.business_ir.validation import validate_business_plan
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.verification.models import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)


def verify_business_plan_candidate(
    candidate: PlanCandidate,
    *,
    is_semantic_capability: (Callable[[str], bool] | None) = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> VerificationResult:
    issues: list[VerificationIssue] = []

    for error in validate_business_plan(
        candidate.business_plan,
        is_semantic_capability=is_semantic_capability,
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    ):
        issues.append(
            VerificationIssue(
                code=error.code,
                severity=VerificationSeverity.ERROR,
                message=error.message,
                location="business_plan",
                details=error.details,
            )
        )

    return VerificationResult(
        passed=not issues,
        issues=issues,
    )
