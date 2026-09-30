import pytest

from app.tcos.compiler import compile_business_plan
from app.tcos.execution import (
    ExecutionCoordinator,
    ExecutionStatus,
)
from app.tcos.planner.runtime.intent import detect_intent
from app.tcos.planner.runtime.planner import Planner
from app.tcos.planner.runtime.planning_context import PlanningContext


GOAL = "Summarize https://example.com"


class FakeAdapter:
    async def execute(
        self,
        *,
        workflow,
        message,
        ctx,
        strict=True,
    ):
        return {
            "answer": "ok",
            "meta": {
                "status": "ok",
                "node_count": len(
                    workflow["nodes"]
                ),
            },
        }


class FailingAdapter:
    async def execute(
        self,
        *,
        workflow,
        message,
        ctx,
        strict=True,
    ):
        raise RuntimeError("boom")


def _execution_graph():
    candidate = Planner().plan(
        intent=detect_intent(
            text=GOAL
        ),
        context=PlanningContext(
            user_message=GOAL,
        ),
    )

    return compile_business_plan(
        candidate.business_plan
    ).execution_graph


@pytest.mark.asyncio
async def test_execution_coordinator_execute_with_adapter():
    session = await ExecutionCoordinator().execute(
        _execution_graph(),
        ctx=object(),
        message="Hello",
        adapter=FakeAdapter(),
    )

    assert session.status == ExecutionStatus.COMPLETED
    assert session.runtime_result["answer"] == "ok"
    assert session.metrics["runtime_status"] == "ok"

    event_types = [
        event.type
        for event in session.events
    ]

    assert event_types == [
        "ExecutionPreparationStarted",
        "RuntimeWorkflowPrepared",
        "RuntimeExecutionStarted",
        "RuntimeExecutionCompleted",
    ]


@pytest.mark.asyncio
async def test_execution_coordinator_execute_handles_adapter_failure():
    session = await ExecutionCoordinator().execute(
        _execution_graph(),
        ctx=object(),
        message="Hello",
        adapter=FailingAdapter(),
    )

    assert session.status == ExecutionStatus.FAILED
    assert session.runtime_result["error"] == "boom"
    assert (
        session.events[-1].type
        == "RuntimeExecutionFailed"
    )
