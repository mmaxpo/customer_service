from __future__ import annotations

from app.tcos.compiler.execution_ir.models import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
)


def execution_graph_from_runtime_workflow(
    workflow: dict,
    *,
    graph_id: str = "imported_runtime_workflow",
) -> ExecutionGraph:
    nodes: list[ExecutionNode] = []
    edges: list[ExecutionEdge] = []

    for node in workflow.get("nodes", []):
        data = dict(node.get("data") or {})
        node_type = data.pop("nodeType")

        inputs = data.pop("inputs", [])
        outputs = data.pop("outputs", [])

        nodes.append(
            ExecutionNode(
                id=node.get("id"),
                node_type=node_type,
                config=data,
                inputs=inputs,
                outputs=outputs,
                metadata={"imported_from": "runtime_workflow"},
            )
        )

    for edge in workflow.get("edges", []):
        edges.append(
            ExecutionEdge(
                id=edge.get("id"),
                source=edge.get("source"),
                target=edge.get("target"),
                condition=edge.get("condition"),
                metadata={"imported_from": "runtime_workflow"},
            )
        )

    return ExecutionGraph(
        id=graph_id,
        nodes=nodes,
        edges=edges,
    )
