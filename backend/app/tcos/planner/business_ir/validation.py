from __future__ import annotations

from collections.abc import Callable

from dataclasses import dataclass, field

from app.tcos.planner.business_ir.models import BusinessPlan


@dataclass(frozen=True)
class BusinessIRValidationError:
    code: str
    message: str
    details: dict = field(default_factory=dict)


def validate_business_plan(
    plan: BusinessPlan,
    *,
    is_semantic_capability: (Callable[[str], bool] | None) = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> list[BusinessIRValidationError]:
    errors: list[BusinessIRValidationError] = []

    task_ids = [task.id for task in plan.tasks]
    task_id_set = set(task_ids)

    if len(task_ids) != len(task_id_set):
        errors.append(
            BusinessIRValidationError(
                code="duplicate_task_id",
                message="Business plan contains duplicate task ids.",
            )
        )

    if not plan.tasks:
        errors.append(
            BusinessIRValidationError(
                code="no_tasks",
                message="Business plan must contain at least one task.",
            )
        )

    for edge in plan.edges:
        if edge.source not in task_id_set:
            errors.append(
                BusinessIRValidationError(
                    code="edge_unknown_source",
                    message=f"Edge source `{edge.source}` does not exist.",
                    details={"edge_id": edge.id, "source": edge.source},
                )
            )

        if edge.target not in task_id_set:
            errors.append(
                BusinessIRValidationError(
                    code="edge_unknown_target",
                    message=f"Edge target `{edge.target}` does not exist.",
                    details={"edge_id": edge.id, "target": edge.target},
                )
            )

        if edge.source == edge.target:
            errors.append(
                BusinessIRValidationError(
                    code="self_loop",
                    message="Business plan edge cannot point to itself.",
                    details={"edge_id": edge.id, "task_id": edge.source},
                )
            )

    missing_capabilities = _missing_capability_ids(
        plan,
        is_semantic_capability=is_semantic_capability,
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )
    if missing_capabilities:
        errors.append(
            BusinessIRValidationError(
                code="missing_capability",
                message="Business plan references capabilities that do not exist.",
                details={"capability_ids": missing_capabilities},
            )
        )

    errors.extend(_validate_cycles(plan))

    return errors


def _validate_cycles(plan: BusinessPlan) -> list[BusinessIRValidationError]:
    task_ids = {task.id for task in plan.tasks}
    outgoing = {task_id: [] for task_id in task_ids}

    for edge in plan.edges:
        if edge.source in task_ids and edge.target in task_ids:
            outgoing[edge.source].append(edge.target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str, path: list[str]) -> list[str] | None:
        if node_id in visiting:
            return path + [node_id]

        if node_id in visited:
            return None

        visiting.add(node_id)

        for target in outgoing.get(node_id, []):
            cycle = visit(target, path + [node_id])
            if cycle:
                return cycle

        visiting.remove(node_id)
        visited.add(node_id)
        return None

    for task_id in task_ids:
        cycle = visit(task_id, [])
        if cycle:
            return [
                BusinessIRValidationError(
                    code="cycle_detected",
                    message="Business plan must be a DAG.",
                    details={"cycle_path": cycle},
                )
            ]

    return []


def _missing_capability_ids(
    plan: BusinessPlan,
    *,
    is_semantic_capability: (Callable[[str], bool] | None) = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> list[str]:
    from app.tcos.planner.business_ir.capabilities import (
        missing_capability_ids,
    )

    return missing_capability_ids(
        plan,
        is_semantic_capability=is_semantic_capability,
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )
