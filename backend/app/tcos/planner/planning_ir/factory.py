from __future__ import annotations

from app.tcos.planner.planning_ir.models import (
    ArtifactKind,
    PlanningArtifact,
    ArtifactReference,
    PlanningPlan,
    PlanningOperation,
)


def artifact(
    *,
    artifact_id: str,
    kind: ArtifactKind,
    description: str = "",
    producer_task_id: str | None = None,
) -> PlanningArtifact:
    return PlanningArtifact(
        id=artifact_id,
        kind=kind,
        description=description,
        producer_task_id=producer_task_id,
    )


def artifact_ref(
    artifact_id: str,
    *,
    required: bool = True,
) -> ArtifactReference:
    return ArtifactReference(
        artifact_id=artifact_id,
        required=required,
    )


def planning_operation(
    *,
    operation_id: str,
    business_task_id: str,
    objective: str,
    selected_capability: str,
    operation_type: str = "generic",
    candidate_capabilities: list[str] | None = None,
    reasoning: str = "",
) -> PlanningOperation:
    return PlanningOperation(
        id=operation_id,
        business_task_id=business_task_id,
        objective=objective,
        operation_type=operation_type,
        selected_capability=selected_capability,
        candidate_capabilities=candidate_capabilities or [selected_capability],
        reasoning=reasoning,
    )


def planning_task(
    *,
    task_id: str,
    business_task_id: str,
    capability_id: str,
    reasoning: str = "",
) -> PlanningOperation:
    # Backward-compatible factory. New code should use planning_operation().
    return planning_operation(
        operation_id=task_id,
        business_task_id=business_task_id,
        objective=task_id,
        selected_capability=capability_id,
        reasoning=reasoning,
    )


def planning_plan(
    *,
    plan_id: str,
    business_plan_id: str,
) -> PlanningPlan:
    return PlanningPlan(
        id=plan_id,
        business_plan_id=business_plan_id,
    )
