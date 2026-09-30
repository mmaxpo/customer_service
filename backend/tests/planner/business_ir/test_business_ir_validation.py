from app.tcos.planner.business_ir import (
    BusinessEdge,
    BusinessGoal,
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
    validate_business_plan,
)


def _task(task_id: str) -> BusinessTask:
    return BusinessTask(
        id=task_id,
        name=task_id,
        category=BusinessTaskCategory.ACTION,
    )


def test_validate_business_plan_accepts_valid_dag():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[_task("a"), _task("b")],
        edges=[BusinessEdge(id="e", source="a", target="b")],
    )

    assert validate_business_plan(plan) == []


def test_validate_business_plan_rejects_unknown_edge_endpoint():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[_task("a")],
        edges=[BusinessEdge(id="e", source="a", target="missing")],
    )

    errors = validate_business_plan(plan)

    assert any(error.code == "edge_unknown_target" for error in errors)


def test_validate_business_plan_rejects_cycle():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[_task("a"), _task("b")],
        edges=[
            BusinessEdge(id="e1", source="a", target="b"),
            BusinessEdge(id="e2", source="b", target="a"),
        ],
    )

    errors = validate_business_plan(plan)

    assert any(error.code == "cycle_detected" for error in errors)
