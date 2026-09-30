from __future__ import annotations

import json

from app.tcos.compiler.execution_ir.models import ExecutionGraph


def execution_graph_to_runtime_workflow(graph: ExecutionGraph) -> dict:
    return {
        "nodes": [
            {
                "id": node.id,
                "data": {
                    "nodeType": node.node_type,
                    **node.config,
                    **({"inputs": node.inputs} if node.inputs else {}),
                    **({"outputs": node.outputs} if node.outputs else {}),
                },
            }
            for node in graph.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                **({"condition": edge.condition} if edge.condition else {}),
                **edge.mapping,
            }
            for edge in graph.edges
        ],
    }


def execution_graph_to_json(graph: ExecutionGraph) -> str:
    return graph.model_dump_json()


def execution_graph_from_json(raw: str) -> ExecutionGraph:
    return ExecutionGraph.model_validate(json.loads(raw))
