from app.tcos.compiler.execution_ir import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    execution_graph_from_json,
    execution_graph_to_json,
    execution_graph_to_runtime_workflow,
)


def test_execution_graph_to_runtime_workflow_shape():
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

    workflow = execution_graph_to_runtime_workflow(graph)

    assert workflow["nodes"][0]["data"]["nodeType"] == "trigger.message"
    assert workflow["nodes"][0]["data"]["input"] == "hello"
    assert workflow["edges"][0]["source"] == "trigger"


def test_execution_graph_json_roundtrip():
    graph = ExecutionGraph(
        id="g",
        nodes=[ExecutionNode(id="response", node_type="response")],
    )

    assert execution_graph_from_json(execution_graph_to_json(graph)) == graph
