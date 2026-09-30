from app.tcos.planner.business_ir import (
    BusinessEdge,
    BusinessGoal,
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
    calculate_business_plan_metrics,
)


def test_calculate_business_plan_metrics():
    plan = BusinessPlan(
        id="p",
        goal=BusinessGoal(id="g", title="Goal"),
        tasks=[
            BusinessTask(
                id="a",
                name="A",
                category=BusinessTaskCategory.ACTION,
                estimated_duration_ms=10,
                estimated_cost=0.2,
            ),
            BusinessTask(
                id="b",
                name="B",
                category=BusinessTaskCategory.ACTION,
                estimated_duration_ms=5,
                estimated_cost=0.3,
            ),
        ],
        edges=[BusinessEdge(id="e1", source="a", target="b")],
    )

    metrics = calculate_business_plan_metrics(plan)

    assert metrics.task_count == 2
    assert metrics.edge_count == 1
    assert metrics.entry_task_count == 1
    assert metrics.exit_task_count == 1
    assert metrics.critical_path_length == 2
    assert metrics.estimated_duration_ms == 15
    assert metrics.estimated_cost == 0.5
