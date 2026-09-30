from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.tcos.compiler.execution_ir.models import ExecutionGraph


class ExecutionGraphAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_count: int
    edge_count: int
    node_types: list[str]
    entry_nodes: list[str]
    exit_nodes: list[str]


def analyze_execution_graph(graph: ExecutionGraph) -> ExecutionGraphAnalysis:
    node_ids = {node.id for node in graph.nodes}
    targets = {edge.target for edge in graph.edges}
    sources = {edge.source for edge in graph.edges}

    return ExecutionGraphAnalysis(
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        node_types=sorted({node.node_type for node in graph.nodes}),
        entry_nodes=sorted(node_ids - targets),
        exit_nodes=sorted(node_ids - sources),
    )
