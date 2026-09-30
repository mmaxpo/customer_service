from app.tcos.compiler.execution_ir import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    validate_execution_graph,
)


def test_validate_execution_graph_accepts_runtime_compatible_graph():
    graph = ExecutionGraph(
        id="g",
        nodes=[
            ExecutionNode(id="trigger", node_type="trigger.message"),
            ExecutionNode(id="response", node_type="response"),
        ],
        edges=[ExecutionEdge(id="e1", source="trigger", target="response")],
    )

    assert validate_execution_graph(graph) == []


def test_validate_execution_graph_rejects_unknown_edge_target():
    graph = ExecutionGraph(
        id="g",
        nodes=[ExecutionNode(id="trigger", node_type="trigger.message")],
        edges=[ExecutionEdge(id="e1", source="trigger", target="missing")],
    )

    errors = validate_execution_graph(graph)

    assert any(error.code == "edge_unknown_target" for error in errors)
