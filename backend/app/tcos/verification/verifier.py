from __future__ import annotations

from collections.abc import Callable

from app.tcos.planner.runtime.plan_candidate import PlanCandidate
from app.tcos.verification.business_plan import verify_business_plan_candidate
from app.tcos.verification.execution_ir import verify_candidate_compilation
from app.tcos.verification.confidence import calculate_verification_confidence
from app.tcos.verification.models import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)


def _verify_planning_artifact_contracts(candidate: PlanCandidate) -> VerificationResult:
    issues: list[VerificationIssue] = []
    produced: set[str] = set()

    # First pass directly over Business IR metadata so verification catches
    # artifact contract errors even if PlanningBuilder/Compiler short-circuit.
    for task in candidate.business_plan.tasks:
        config = (task.metadata or {}).get("config") or {}

        answer_from = config.get("answer_from")
        if isinstance(answer_from, str):
            artifact_id = answer_from.strip()
            if (
                artifact_id
                and artifact_id not in {"last", "input"}
                and artifact_id not in produced
            ):
                issues.append(
                    VerificationIssue(
                        code="missing_artifact_producer",
                        severity=VerificationSeverity.ERROR,
                        message=(
                            f"Task `{task.id}` requires artifact `{artifact_id}` "
                            "but no previous task produces it."
                        ),
                        location=f"business_task:{task.id}",
                        details={"artifact_id": artifact_id},
                    )
                )

        produced_artifact = config.get("artifact_as") or config.get("save_as")
        if isinstance(produced_artifact, str) and produced_artifact.strip():
            produced.add(produced_artifact.strip())

    # Second pass over Planning IR when it can be built successfully.
    try:
        from app.tcos.planner.planning_builder import PlanningBuilder

        planning_plan = PlanningBuilder().build(candidate.business_plan)
    except Exception:
        return VerificationResult(passed=not issues, issues=issues)

    produced = set()

    for operation in planning_plan.operations:
        invocation = operation.invocation
        if invocation is None:
            continue

        for item in invocation.inputs:
            if item.required and item.artifact_id not in produced:
                issues.append(
                    VerificationIssue(
                        code="missing_artifact_producer",
                        severity=VerificationSeverity.ERROR,
                        message=(
                            f"Planning operation `{operation.id}` requires artifact "
                            f"`{item.artifact_id}` but no previous operation produces it."
                        ),
                        location=f"planning_operation:{operation.id}",
                        details={"artifact_id": item.artifact_id},
                    )
                )

        for item in invocation.outputs:
            produced.add(item.artifact_id)

    return VerificationResult(passed=not issues, issues=issues)


class VerificationEngine:
    """
    Verifies a selected plan before execution.
    """

    def verify(
        self,
        candidate: PlanCandidate,
        *,
        is_semantic_capability: (Callable[[str], bool] | None) = None,
        runtime_node_for_capability: (
            Callable[[str], str | None] | None
        ) = None,
    ) -> VerificationResult:

        business_result = verify_business_plan_candidate(
            candidate,
            is_semantic_capability=is_semantic_capability,
            runtime_node_for_capability=(
                runtime_node_for_capability
            ),
        )
        artifact_result = _verify_planning_artifact_contracts(candidate)
        compilation_result = verify_candidate_compilation(
            candidate,
            is_semantic_capability=is_semantic_capability,
            runtime_node_for_capability=(
                runtime_node_for_capability
            ),
        )

        issues = [
            *business_result.issues,
            *artifact_result.issues,
            *compilation_result.issues,
        ]

        result = VerificationResult(
            passed=(
                business_result.passed
                and artifact_result.passed
                and compilation_result.passed
            ),
            issues=issues,
        )
        result.confidence = calculate_verification_confidence(result).model_dump(
            mode="json"
        )
        return result
