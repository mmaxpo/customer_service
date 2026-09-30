from __future__ import annotations

from dataclasses import dataclass, field

from app.tcos.compiler.execution_ir.models import ExecutionGraph
from app.tcos.compiler.execution_ir.serialization import (
    execution_graph_to_runtime_workflow,
)
from app.runtime.engine.validator import validate_workflow


@dataclass(frozen=True)
class ExecutionIRValidationError:
    code: str
    message: str
    details: dict = field(default_factory=dict)


def validate_execution_graph(graph: ExecutionGraph) -> list[ExecutionIRValidationError]:
    errors: list[ExecutionIRValidationError] = []

    node_ids = [node.id for node in graph.nodes]

    if len(node_ids) != len(set(node_ids)):
        errors.append(
            ExecutionIRValidationError(
                code="duplicate_node_id",
                message="Execution graph contains duplicate node ids.",
            )
        )

    node_id_set = set(node_ids)

    for edge in graph.edges:
        if edge.source not in node_id_set:
            errors.append(
                ExecutionIRValidationError(
                    code="edge_unknown_source",
                    message=f"Edge source `{edge.source}` does not exist.",
                    details={"edge_id": edge.id},
                )
            )

        if edge.target not in node_id_set:
            errors.append(
                ExecutionIRValidationError(
                    code="edge_unknown_target",
                    message=f"Edge target `{edge.target}` does not exist.",
                    details={"edge_id": edge.id},
                )
            )

    if errors:
        return errors

    runtime_errors = validate_workflow(execution_graph_to_runtime_workflow(graph))

    return [
        ExecutionIRValidationError(
            code=error.code,
            message=error.message,
            details=error.details,
        )
        for error in runtime_errors
    ]
