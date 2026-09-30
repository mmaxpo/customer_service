from __future__ import annotations

from app.tcos.compiler.execution_ir.models import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
)


def simple_runtime_graph(
    *,
    graph_id: str,
    nodes: list[ExecutionNode],
) -> ExecutionGraph:
    edges = [
        ExecutionEdge(
            id=f"edge_{nodes[index].id}_to_{nodes[index + 1].id}",
            source=nodes[index].id,
            target=nodes[index + 1].id,
        )
        for index in range(len(nodes) - 1)
    ]

    return ExecutionGraph(id=graph_id, nodes=nodes, edges=edges)


def trigger_node(*, node_id: str = "trigger", input_text: str = "") -> ExecutionNode:
    return ExecutionNode(
        id=node_id,
        node_type="trigger.message",
        config={"input": input_text},
    )


def response_node(*, node_id: str = "response") -> ExecutionNode:
    return ExecutionNode(id=node_id, node_type="response")
