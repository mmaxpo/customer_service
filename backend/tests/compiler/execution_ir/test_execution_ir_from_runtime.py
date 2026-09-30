from app.tcos.compiler.execution_ir import (
    execution_graph_from_runtime_workflow,
    execution_graph_to_runtime_workflow,
    validate_execution_graph,
)


def test_execution_graph_from_runtime_workflow_roundtrip():
    workflow = {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "hello",
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "last",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "trigger",
                "target": "response",
            }
        ],
    }

    graph = execution_graph_from_runtime_workflow(workflow, graph_id="g")

    assert graph.id == "g"
    assert graph.nodes[0].node_type == "trigger.message"
    assert graph.nodes[0].config["input"] == "hello"
    assert validate_execution_graph(graph) == []

    runtime = execution_graph_to_runtime_workflow(graph)

    assert runtime["nodes"][0]["data"]["nodeType"] == "trigger.message"
    assert runtime["nodes"][0]["data"]["input"] == "hello"
    assert runtime["edges"][0]["source"] == "trigger"
