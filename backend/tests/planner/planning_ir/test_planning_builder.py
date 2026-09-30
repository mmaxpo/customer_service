from app.tcos.planner.business_ir.generic_examples import build_url_summary_business_plan
from app.tcos.planner.business_ir.models import (
    BusinessPlan,
    BusinessGoal,
    BusinessTask,
    BusinessTaskCategory,
)
from app.tcos.planner.planning_builder import (
    PlanningBuilder,
    planning_operation_from_business_task,
)
from app.tcos.planner.planning_ir import validate_planning_plan


def test_planning_operation_from_business_task():
    business_plan = build_url_summary_business_plan("Summarize https://example.com")
    task = business_plan.tasks[0]

    operation = planning_operation_from_business_task(task)

    assert operation.id == task.id
    assert operation.business_task_id == task.id
    assert operation.selected_capability == "runtime.web_fetch_extract"
    assert operation.capability_id == "runtime.web_fetch_extract"
    assert operation.operation_type == "act"


def test_planning_builder_converts_business_plan_to_operations():
    business_plan = build_url_summary_business_plan("Summarize https://example.com")

    planning_plan = PlanningBuilder().build(business_plan)

    assert planning_plan.business_plan_id == business_plan.id
    assert len(planning_plan.operations) == len(business_plan.tasks)
    assert planning_plan.tasks == planning_plan.operations
    assert planning_plan.operations[0].business_task_id == business_plan.tasks[0].id
    assert (
        planning_plan.operations[0].selected_capability == "runtime.web_fetch_extract"
    )


def test_planning_builder_preserves_business_edges_in_metadata():
    business_plan = build_url_summary_business_plan("Summarize https://example.com")

    planning_plan = PlanningBuilder().build(business_plan)

    business_edges = planning_plan.metadata.extra["business_edges"]

    assert len(business_edges) == len(business_plan.edges)
    assert business_edges[0]["source"] == business_plan.edges[0].source
    assert business_edges[0]["target"] == business_plan.edges[0].target


def test_planning_builder_output_validates():
    business_plan = build_url_summary_business_plan("Summarize https://example.com")

    planning_plan = PlanningBuilder().build(business_plan)

    assert validate_planning_plan(planning_plan) == []


def test_planning_builder_fails_for_missing_capability():
    business_plan = BusinessPlan(
        id="bad_plan",
        goal=BusinessGoal(
            id="bad_goal",
            title="Bad goal",
        ),
        tasks=[
            BusinessTask(
                id="task_without_capability",
                name="Task without capability",
                category=BusinessTaskCategory.ACTION,
            )
        ],
    )

    try:
        PlanningBuilder().build(business_plan)
    except ValueError as exc:
        assert "unknown_artifact" not in str(exc)
        assert "capability" in str(exc).lower()
    else:
        raise AssertionError("Expected PlanningBuilder to fail")
