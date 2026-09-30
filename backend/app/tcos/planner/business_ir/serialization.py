from __future__ import annotations

import json

from app.tcos.planner.business_ir.models import BusinessPlan


def business_plan_to_json(plan: BusinessPlan) -> str:
    return plan.model_dump_json()


def business_plan_from_json(raw: str) -> BusinessPlan:
    return BusinessPlan.model_validate(json.loads(raw))


def business_plan_to_runtime_safe_dict(plan: BusinessPlan) -> dict:
    return plan.model_dump(mode="json")
