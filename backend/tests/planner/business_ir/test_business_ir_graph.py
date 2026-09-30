from app.tcos.planner.business_ir import (
    BusinessEdge,
    BusinessGoal,
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
    critical_path_task_ids,
    entry_task_ids,
    exit_task_ids,
    parallel_groups,
    topological_task_ids,
)


def _task(task_id: str, duration: int = 1) -> BusinessTask:
    return BusinessTask(
        id=task_id,
        name=task_id,
        category=BusinessTaskCategory.ACTION,
        estimated_duration_ms=duration,
    )


def test_business_ir_graph_helpers_find_entry_exit_and_order():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[_task("a"), _task("b"), _task("c")],
        edges=[
            BusinessEdge(id="e1", source="a", target="c"),
            BusinessEdge(id="e2", source="b", target="c"),
        ],
    )

    assert entry_task_ids(plan) == ["a", "b"]
    assert exit_task_ids(plan) == ["c"]
    assert topological_task_ids(plan) == ["a", "b", "c"]
    assert parallel_groups(plan) == [["a", "b"], ["c"]]


def test_business_ir_critical_path_uses_estimated_duration():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[_task("a", 10), _task("b", 1), _task("c", 1), _task("d", 1)],
        edges=[
            BusinessEdge(id="e1", source="a", target="d"),
            BusinessEdge(id="e2", source="b", target="c"),
            BusinessEdge(id="e3", source="c", target="d"),
        ],
    )

    assert critical_path_task_ids(plan) == ["a", "d"]
