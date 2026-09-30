from app.tcos.compiler.execution_ir import ExecutionEdge, ExecutionGraph, ExecutionNode


def test_execution_graph_model():
    graph = ExecutionGraph(
        id="g",
        nodes=[
            ExecutionNode(
                id="trigger",
                node_type="trigger.message",
                config={"input": "hello"},
            ),
            ExecutionNode(id="response", node_type="response"),
        ],
        edges=[ExecutionEdge(id="e1", source="trigger", target="response")],
    )

    assert graph.schema_version == "execution_ir.v1"
    assert graph.nodes[0].node_type == "trigger.message"
