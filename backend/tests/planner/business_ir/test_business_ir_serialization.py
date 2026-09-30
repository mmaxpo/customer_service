from app.tcos.planner.business_ir import (
    BusinessGoal,
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
)
from app.tcos.planner.business_ir.serialization import (
    business_plan_from_json,
    business_plan_to_json,
    business_plan_to_runtime_safe_dict,
)


def test_business_plan_json_roundtrip():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[
            BusinessTask(
                id="t",
                name="Task",
                category=BusinessTaskCategory.ACTION,
            )
        ],
    )

    loaded = business_plan_from_json(business_plan_to_json(plan))

    assert loaded == plan


def test_business_plan_runtime_safe_dict():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[
            BusinessTask(
                id="t",
                name="Task",
                category=BusinessTaskCategory.ACTION,
            )
        ],
    )

    data = business_plan_to_runtime_safe_dict(plan)

    assert data["tasks"][0]["category"] == "action"
