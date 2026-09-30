from __future__ import annotations

from app.tcos.planner.business_ir.models import (
    BusinessDependencyType,
    BusinessEdge,
    BusinessGoal,
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
    CapabilityReference,
)


def simple_linear_plan(
    *,
    plan_id: str,
    goal_id: str,
    goal_title: str,
    tasks: list[BusinessTask],
) -> BusinessPlan:
    edges = [
        BusinessEdge(
            id=f"edge_{tasks[index].id}_to_{tasks[index + 1].id}",
            source=tasks[index].id,
            target=tasks[index + 1].id,
            dependency_type=BusinessDependencyType.HARD,
        )
        for index in range(len(tasks) - 1)
    ]

    return BusinessPlan(
        id=plan_id,
        goal=BusinessGoal(id=goal_id, title=goal_title),
        tasks=tasks,
        edges=edges,
    )


def task_with_capability(
    *,
    task_id: str,
    name: str,
    category: BusinessTaskCategory,
    capability_id: str,
    description: str = "",
) -> BusinessTask:
    return BusinessTask(
        id=task_id,
        name=name,
        description=description,
        category=category,
        required_capabilities=[CapabilityReference(capability_id=capability_id)],
    )
