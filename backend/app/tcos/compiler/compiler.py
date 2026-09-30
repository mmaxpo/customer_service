from __future__ import annotations

from typing import Callable

from app.tcos.compiler.capability_mapping import runtime_mapping_for_capability
from app.tcos.compiler.diagnostics import CompilerDiagnostic, CompilerDiagnosticSeverity
from app.tcos.compiler.execution_ir.models import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionGraphMetadata,
    ExecutionNode,
)
from app.tcos.compiler.execution_ir.validation import validate_execution_graph
from app.tcos.compiler.result import CompilationResult
from app.tcos.planner.business_ir.models import BusinessPlan
from app.tcos.planner.business_ir.validation import validate_business_plan
from app.tcos.planner.planning_builder import PlanningBuilder
from app.tcos.planner.planning_ir import PlanningPlan


def _validate_artifact_contracts(
    nodes: list[ExecutionNode],
) -> list[CompilerDiagnostic]:
    diagnostics: list[CompilerDiagnostic] = []
    produced: set[str] = set()

    for node in nodes:
        for item in node.inputs:
            artifact_id = item.get("artifact_id")
            required = item.get("required", True)

            if required and artifact_id and artifact_id not in produced:
                diagnostics.append(
                    CompilerDiagnostic(
                        severity=CompilerDiagnosticSeverity.ERROR,
                        code="missing_artifact_producer",
                        message=f"Node `{node.id}` requires artifact `{artifact_id}` but no previous node produces it.",
                        location=f"execution_node:{node.id}",
                        details={"artifact_id": artifact_id},
                    )
                )

        for item in node.outputs:
            artifact_id = item.get("artifact_id")
            if artifact_id:
                produced.add(artifact_id)

    return diagnostics


def _bind_capability_invoke_artifacts(
    *,
    config: dict,
    node_inputs: list[dict],
    node_outputs: list[dict],
) -> None:
    """
    Translate Planning IR artifact contracts into the existing
    capability.invoke runtime data contract.

    Explicit runtime configuration always wins. The compiler only
    fills missing values.
    """

    input_artifact_ids = [
        str(item["artifact_id"]) for item in node_inputs if item.get("artifact_id")
    ]

    if input_artifact_ids:
        config.setdefault("input_from", "vars")

        if (
            config.get("input_from") == "vars"
            and "input_key" not in config
            and "input_keys" not in config
        ):
            if len(input_artifact_ids) == 1:
                config["input_key"] = input_artifact_ids[0]
            else:
                config["input_keys"] = input_artifact_ids

    output_artifact_ids = [
        str(item["artifact_id"]) for item in node_outputs if item.get("artifact_id")
    ]

    # capability.invoke currently returns one result value.
    # A single Planning IR result artifact can therefore map
    # directly to the runtime variable name.
    if len(output_artifact_ids) == 1:
        config.setdefault(
            "save_as",
            output_artifact_ids[0],
        )


def compile_planning_plan(
    plan: PlanningPlan,
    *,
    is_semantic_capability: Callable[[str], bool] | None = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> CompilationResult:
    diagnostics: list[CompilerDiagnostic] = []

    nodes: list[ExecutionNode] = []
    edges: list[ExecutionEdge] = []

    nodes.append(
        ExecutionNode(
            id="trigger",
            node_type="trigger.message",
            config={"input": ""},
            metadata={
                "compiler_inserted": True,
                "reason": "workflow_entrypoint",
            },
        )
    )

    first_operation_id = plan.operations[0].id if plan.operations else None

    if first_operation_id:
        edges.append(
            ExecutionEdge(
                id=f"edge_trigger_to_{first_operation_id}",
                source="trigger",
                target=first_operation_id,
            )
        )

    for operation in plan.operations:
        invocation = operation.invocation
        capability_id = (
            invocation.capability_id
            if invocation is not None
            else operation.selected_capability
        )

        if not capability_id:
            diagnostics.append(
                CompilerDiagnostic(
                    severity=CompilerDiagnosticSeverity.ERROR,
                    code="task_missing_capability",
                    message=f"Planning operation `{operation.id}` has no selected capability.",
                    location=f"planning_operation:{operation.id}",
                )
            )
            continue

        mapping = runtime_mapping_for_capability(
            capability_id,
            is_semantic_capability=(
                is_semantic_capability
            ),
            runtime_node_for_capability=(
                runtime_node_for_capability
            ),
        )

        if mapping is None:
            diagnostics.append(
                CompilerDiagnostic(
                    severity=CompilerDiagnosticSeverity.ERROR,
                    code="capability_not_compilable",
                    message=f"Capability `{capability_id}` cannot be compiled.",
                    location=f"planning_operation:{operation.id}",
                )
            )
            continue

        invocation_args = invocation.arguments if invocation is not None else {}

        config = {
            **mapping.default_config,
            **invocation_args,
            "name": operation.objective,
        }

        if invocation is not None:
            timeout_ms = invocation.execution.timeout_ms or invocation.timeout_ms
            retry_count = invocation.execution.retry_count or invocation.retry_count
            retry_backoff_ms = invocation.execution.retry_backoff_ms

            if timeout_ms is not None:
                config.setdefault("timeout_ms", timeout_ms)
            if retry_count:
                config.setdefault("retries", retry_count)
            if retry_backoff_ms:
                config.setdefault("retry_backoff_ms", retry_backoff_ms)

        if mapping.node_type == "response":
            answer_from = config.get("answer_from")

            if answer_from and answer_from not in {"last", "vars"}:
                config["answer_from"] = "vars"
                config.setdefault("answer_key", answer_from)
            else:
                config.setdefault("answer_from", "last")

        node_inputs = []
        node_outputs = []

        if invocation is not None and invocation.inputs:
            node_inputs = [
                {"artifact_id": item.artifact_id, "required": item.required}
                for item in invocation.inputs
            ]
        else:
            node_inputs = [
                {"artifact_id": item.artifact_id, "required": item.required}
                for item in operation.consumes
            ]

        if invocation is not None and invocation.outputs:
            node_outputs = [
                {"artifact_id": item.artifact_id, "kind": item.kind}
                for item in invocation.outputs
            ]
        else:
            node_outputs = [
                {"artifact_id": item.id, "kind": item.kind.value}
                for item in operation.produces
            ]

        if mapping.node_type == "capability.invoke":
            _bind_capability_invoke_artifacts(
                config=config,
                node_inputs=node_inputs,
                node_outputs=node_outputs,
            )

        nodes.append(
            ExecutionNode(
                id=operation.id,
                node_type=mapping.node_type,
                config=config,
                inputs=node_inputs,
                outputs=node_outputs,
                metadata={
                    "business_task_id": operation.business_task_id,
                    "planning_operation_id": operation.id,
                    "capability_id": capability_id,
                    "operation_type": operation.operation_type,
                    "invocation_contract": {
                        "capability_id": capability_id,
                        "arguments": invocation.arguments
                        if invocation is not None
                        else {},
                        "inputs": node_inputs,
                        "outputs": node_outputs,
                        "execution": (
                            invocation.execution.model_dump(mode="json")
                            if invocation is not None
                            else {}
                        ),
                    },
                },
            )
        )

    for edge in plan.metadata.extra.get("business_edges", []):
        edges.append(
            ExecutionEdge(
                id=edge.get("id"),
                source=edge.get("source"),
                target=edge.get("target"),
                condition=edge.get("condition"),
                metadata={
                    "business_edge_id": edge.get("id"),
                    "dependency_type": edge.get("dependency_type"),
                },
            )
        )

    graph = ExecutionGraph(
        id=f"execution_{plan.business_plan_id}",
        nodes=nodes,
        edges=edges,
        metadata=ExecutionGraphMetadata(
            source_business_plan_id=plan.business_plan_id,
            estimated_cost=None,
            estimated_latency_ms=None,
            extra={
                "compiler": "planning_ir_v1",
                "source_planning_plan_id": plan.id,
            },
        ),
    )

    diagnostics.extend(_validate_artifact_contracts(nodes))

    execution_errors = validate_execution_graph(graph)
    diagnostics.extend(
        [
            CompilerDiagnostic(
                severity=CompilerDiagnosticSeverity.ERROR,
                code=error.code,
                message=error.message,
                location="execution_ir",
                details=error.details,
            )
            for error in execution_errors
        ]
    )

    return CompilationResult(
        ok=not any(d.severity == CompilerDiagnosticSeverity.ERROR for d in diagnostics),
        execution_graph=None if diagnostics else graph,
        diagnostics=diagnostics,
    )


def compile_business_plan(
    plan: BusinessPlan,
    *,
    is_semantic_capability: Callable[[str], bool] | None = None,
    runtime_node_for_capability: (
        Callable[[str], str | None] | None
    ) = None,
) -> CompilationResult:
    business_errors = validate_business_plan(
        plan,
        is_semantic_capability=is_semantic_capability,
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )
    if business_errors:
        return CompilationResult(
            ok=False,
            diagnostics=[
                CompilerDiagnostic(
                    severity=CompilerDiagnosticSeverity.ERROR,
                    code=error.code,
                    message=error.message,
                    location="business_ir",
                    details=error.details,
                )
                for error in business_errors
            ],
        )

    try:
        planning_plan = PlanningBuilder().build(plan)
    except ValueError as exc:
        return CompilationResult(
            ok=False,
            diagnostics=[
                CompilerDiagnostic(
                    severity=CompilerDiagnosticSeverity.ERROR,
                    code="task_missing_capability",
                    message=str(exc),
                    location="planning_ir",
                    details={},
                )
            ],
        )

    return compile_planning_plan(
        planning_plan,
        is_semantic_capability=is_semantic_capability,
        runtime_node_for_capability=(
            runtime_node_for_capability
        ),
    )
