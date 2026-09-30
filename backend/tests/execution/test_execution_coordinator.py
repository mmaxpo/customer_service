from app.tcos.compiler import compile_business_plan
from app.tcos.execution import (
    ExecutionBackend,
    ExecutionCoordinator,
    ExecutionStatus,
)
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.planner import Planner
from app.tcos.planner.runtime.planning_context import PlanningContext


GOAL = "Summarize https://example.com"


def _candidate():
    return Planner().plan(
        intent=detect_intent(text=GOAL),
        context=PlanningContext(
            user_message=GOAL,
        ),
    )


def test_execution_coordinator_prepares_runtime_workflow():
    candidate = _candidate()

    compilation = compile_business_plan(
        candidate.business_plan
    )

    session = ExecutionCoordinator().prepare(
        compilation.execution_graph,
        backend=ExecutionBackend.WORKFLOW_RUNTIME,
    )

    assert session.status == ExecutionStatus.COMPLETED
    assert session.runtime_workflow is not None
    assert session.metrics["node_count"] > 0
    assert session.metrics["edge_count"] > 0


def test_execution_events():
    candidate = _candidate()

    graph = compile_business_plan(
        candidate.business_plan
    ).execution_graph

    session = ExecutionCoordinator().prepare(
        graph
    )

    assert [
        event.type
        for event in session.events
    ] == [
        "ExecutionPreparationStarted",
        "RuntimeWorkflowPrepared",
    ]
