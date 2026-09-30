from __future__ import annotations

from pydantic import BaseModel

from app.tcos.planner.business_ir.capabilities import capability_ids_for_plan
from app.tcos.planner.business_ir.graph import (
    critical_path_task_ids,
    entry_task_ids,
    exit_task_ids,
    parallel_groups,
)
from app.tcos.planner.business_ir.metrics import calculate_business_plan_metrics
from app.tcos.planner.business_ir.models import BusinessPlan


class BusinessPlanAnalysis(BaseModel):
    capability_ids: list[str]
    entry_tasks: list[str]
    exit_tasks: list[str]
    critical_path: list[str]
    parallel_groups: list[list[str]]
    metrics: dict


def analyze_business_plan(plan: BusinessPlan) -> BusinessPlanAnalysis:
    metrics = calculate_business_plan_metrics(plan)

    return BusinessPlanAnalysis(
        capability_ids=capability_ids_for_plan(plan),
        entry_tasks=entry_task_ids(plan),
        exit_tasks=exit_task_ids(plan),
        critical_path=critical_path_task_ids(plan),
        parallel_groups=parallel_groups(plan),
        metrics=metrics.model_dump(),
    )
