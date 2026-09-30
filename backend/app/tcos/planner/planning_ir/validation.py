from __future__ import annotations

from dataclasses import dataclass

from app.tcos.planner.planning_ir.models import PlanningPlan


@dataclass(frozen=True)
class PlanningValidationError:
    code: str
    message: str


def validate_planning_plan(
    plan: PlanningPlan,
) -> list[PlanningValidationError]:

    errors: list[PlanningValidationError] = []

    task_ids = set()

    for task in plan.tasks:
        if task.id in task_ids:
            errors.append(
                PlanningValidationError(
                    code="duplicate_task_id",
                    message=f"Duplicate planning task id '{task.id}'.",
                )
            )
        task_ids.add(task.id)

    artifact_ids = set()

    for artifact in plan.artifacts:
        if artifact.id in artifact_ids:
            errors.append(
                PlanningValidationError(
                    code="duplicate_artifact_id",
                    message=f"Duplicate artifact id '{artifact.id}'.",
                )
            )
        artifact_ids.add(artifact.id)

    for task in plan.tasks:
        if not task.capability_id:
            errors.append(
                PlanningValidationError(
                    code="missing_capability",
                    message=f"Planning operation '{task.id}' has no selected capability.",
                )
            )

    for task in plan.tasks:
        for ref in task.consumes:
            if ref.artifact_id not in artifact_ids:
                errors.append(
                    PlanningValidationError(
                        code="unknown_artifact",
                        message=(
                            f"Task '{task.id}' references unknown "
                            f"artifact '{ref.artifact_id}'."
                        ),
                    )
                )

    return errors
