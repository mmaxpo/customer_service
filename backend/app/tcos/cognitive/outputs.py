from __future__ import annotations

from app.tcos.compiler.execution_ir import execution_graph_to_runtime_workflow
from app.tcos.cognitive.models import CognitiveSession


def compiled_runtime_workflow_from_session(session: CognitiveSession) -> dict | None:
    planner = session.planner_session or {}
    compilation = planner.get("compilation") or {}

    if not compilation.get("ok"):
        return None

    execution_graph = compilation.get("execution_graph")

    if not execution_graph:
        return None

    from app.tcos.compiler.execution_ir.models import ExecutionGraph

    graph = ExecutionGraph.model_validate(execution_graph)
    return execution_graph_to_runtime_workflow(graph)
