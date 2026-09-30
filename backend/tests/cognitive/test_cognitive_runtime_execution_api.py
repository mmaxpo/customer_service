import pytest

from app.tcos.cognitive import CognitiveRuntime
from app.tcos.execution import ExecutionStatus


class FakeAdapter:
    async def execute(self, *, workflow, message, ctx, strict=True):
        return {
            "answer": "ok",
            "meta": {
                "status": "ok",
            },
        }


@pytest.mark.asyncio
async def test_runtime_api_exists():
    runtime = CognitiveRuntime()

    assert hasattr(runtime, "execute_goal_runtime")


@pytest.mark.asyncio
async def test_execute_goal_runtime_uses_execution_session_graph(monkeypatch):
    from app.tcos.execution.coordinator import ExecutionCoordinator

    original_execute = ExecutionCoordinator.execute

    async def fake_execute(
        self, execution_graph, *, ctx, message, strict=True, backend=None, adapter=None
    ):
        return await original_execute(
            self,
            execution_graph,
            ctx=ctx,
            message=message,
            strict=strict,
            adapter=FakeAdapter(),
        )

    monkeypatch.setattr(ExecutionCoordinator, "execute", fake_execute)

    session = await CognitiveRuntime().execute_goal_runtime(
        goal="Summarize https://example.com",
        ctx=object(),
    )

    assert session.metrics["runtime_executed"] is True
    assert session.execution_session["status"] == ExecutionStatus.COMPLETED
    assert session.execution_session["runtime_result"]["answer"] == "ok"
    assert session.events[-1].type == "RuntimeExecutionFinished"
