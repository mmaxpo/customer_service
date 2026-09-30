from __future__ import annotations

from collections.abc import Callable

from app.tcos.compiler.compiler import compile_business_plan
from app.tcos.compiler.diagnostics import CompilerDiagnosticSeverity
from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.verification.models import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)


def verify_candidate_compilation(
    candidate: PlanCandidate,
    *,
    is_semantic_capability: (Callable[[str], bool] | None) = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> VerificationResult:
    compilation = compile_business_plan(
        candidate.business_plan,
        is_semantic_capability=is_semantic_capability,
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )

    issues: list[VerificationIssue] = [
        VerificationIssue(
            code=diagnostic.code,
            severity=(
                VerificationSeverity.ERROR
                if diagnostic.severity == CompilerDiagnosticSeverity.ERROR
                else VerificationSeverity.WARNING
            ),
            message=diagnostic.message,
            location=diagnostic.location,
            details=diagnostic.details,
        )
        for diagnostic in compilation.diagnostics
    ]

    return VerificationResult(
        passed=compilation.ok,
        issues=issues,
    )
