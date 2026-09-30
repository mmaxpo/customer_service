from app.tcos.planner.planning_ir import (
    PlanningOperation,
    PlanningPlan,
    PlanningTask,
    planning_operation,
    planning_task,
)


def test_planning_operation_is_canonical_model():
    op = PlanningOperation(
        id="fetch_url",
        business_task_id="fetch_url",
        objective="Acquire web document",
        operation_type="acquire",
        selected_capability="runtime.web_fetch_extract",
    )

    assert op.selected_capability == "runtime.web_fetch_extract"
    assert op.capability_id == "runtime.web_fetch_extract"


def test_planning_task_alias_still_works():
    task = PlanningTask(
        id="respond",
        business_task_id="respond",
        objective="Send response",
        operation_type="communicate",
        selected_capability="runtime.response",
    )

    assert isinstance(task, PlanningOperation)
    assert task.capability_id == "runtime.response"


def test_planning_plan_tasks_property_maps_to_operations():
    op = planning_operation(
        operation_id="summarize",
        business_task_id="summarize",
        objective="Summarize content",
        operation_type="understand",
        selected_capability="runtime.llm_generate",
    )

    plan = PlanningPlan(
        id="planning_test",
        business_plan_id="business_test",
        operations=[op],
    )

    assert plan.tasks == plan.operations
    assert plan.tasks[0].objective == "Summarize content"


def test_legacy_planning_task_factory_still_works():
    task = planning_task(
        task_id="respond",
        business_task_id="respond",
        capability_id="runtime.response",
        reasoning="Send the final answer.",
    )

    assert isinstance(task, PlanningOperation)
    assert task.id == "respond"
    assert task.selected_capability == "runtime.response"
    assert task.capability_id == "runtime.response"
