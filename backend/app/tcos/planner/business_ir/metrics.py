from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.tcos.planner.business_ir.graph import (
    critical_path_task_ids,
    entry_task_ids,
    exit_task_ids,
    parallel_groups,
)
from app.tcos.planner.business_ir.models import BusinessPlan


class BusinessPlanMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_count: int
    edge_count: int
    entry_task_count: int
    exit_task_count: int
    parallel_group_count: int
    critical_path_length: int
    estimated_duration_ms: int
    estimated_cost: float


def calculate_business_plan_metrics(plan: BusinessPlan) -> BusinessPlanMetrics:
    critical_path = critical_path_task_ids(plan)
    tasks_by_id = {task.id: task for task in plan.tasks}

    return BusinessPlanMetrics(
        task_count=len(plan.tasks),
        edge_count=len(plan.edges),
        entry_task_count=len(entry_task_ids(plan)),
        exit_task_count=len(exit_task_ids(plan)),
        parallel_group_count=len(parallel_groups(plan)),
        critical_path_length=len(critical_path),
        estimated_duration_ms=sum(
            (tasks_by_id[task_id].estimated_duration_ms or 1)
            for task_id in critical_path
        ),
        estimated_cost=sum(task.estimated_cost or 0 for task in plan.tasks),
    )
