from __future__ import annotations

from app.tcos.planner.business_ir.models import (
    BusinessPlan,
    BusinessTask,
    BusinessTaskCategory,
)

from app.tcos.planner.planning_ir import (
    ArtifactKind,
    ArtifactReference,
    InvocationExecutionPolicy,
    InvocationInput,
    InvocationOutput,
    PlanningArtifact,
    PlanningCapabilityInvocation,
    PlanningOperation,
    PlanningPlan,
    PlanningMetadata,
    validate_planning_plan,
)


def _artifact_refs_for_operation_config(config: dict) -> list[ArtifactReference]:
    refs: list[ArtifactReference] = []

    for key, value in config.items():
        if not isinstance(value, str):
            continue

        if "{{ web_extract.text }}" in value:
            refs.append(ArtifactReference(artifact_id="web_extract"))

        if "{{ summary }}" in value:
            refs.append(ArtifactReference(artifact_id="summary"))

        if key == "answer_from" and value.strip() not in {"", "last", "input"}:
            refs.append(ArtifactReference(artifact_id=value.strip()))

    seen: set[str] = set()
    unique: list[ArtifactReference] = []

    for ref in refs:
        if ref.artifact_id in seen:
            continue
        seen.add(ref.artifact_id)
        unique.append(ref)

    return unique


def _artifact_kind_for_capability(capability_id: str) -> ArtifactKind:
    if capability_id == "runtime.web_fetch_extract":
        return ArtifactKind.DOCUMENT
    if (
        capability_id == "runtime.kb_search"
        or capability_id == "agent_tool.knowledge_search"
    ):
        return ArtifactKind.KNOWLEDGE
    if capability_id == "runtime.response":
        return ArtifactKind.RESPONSE
    return ArtifactKind.TEXT


def _produced_artifact_for_operation(
    *,
    operation_id: str,
    capability_id: str,
    artifact_id: str | None,
) -> PlanningArtifact | None:
    if not artifact_id:
        return None

    return PlanningArtifact(
        id=artifact_id,
        kind=_artifact_kind_for_capability(capability_id),
        description=f"Artifact produced by planning operation {operation_id}.",
        producer_task_id=operation_id,
    )


def _operation_type_for_category(category: BusinessTaskCategory) -> str:
    mapping = {
        BusinessTaskCategory.INFORMATION: "acquire_information",
        BusinessTaskCategory.DECISION: "decide",
        BusinessTaskCategory.VALIDATION: "validate",
        BusinessTaskCategory.ACTION: "act",
        BusinessTaskCategory.COMMUNICATION: "communicate",
        BusinessTaskCategory.APPROVAL: "approve",
        BusinessTaskCategory.VERIFICATION: "verify",
    }
    return mapping.get(category, "generic")


def _selected_capability_for_task(task: BusinessTask) -> str:
    if not task.required_capabilities:
        return ""

    return task.required_capabilities[0].capability_id


def planning_operation_from_business_task(task: BusinessTask) -> PlanningOperation:
    selected_capability = _selected_capability_for_task(task)

    operation_metadata = {
        "business_task_name": task.name,
        "business_category": task.category.value,
        "business_priority": task.priority,
        "business_metadata": task.metadata,
    }

    # Cognitive-layer execution hints:
    # Business IR may carry semantic configuration, but the compiler should read
    # it from PlanningOperation.metadata["config"], not from BusinessTask.
    if isinstance(task.metadata, dict) and isinstance(
        task.metadata.get("config"), dict
    ):
        operation_metadata["config"] = dict(task.metadata["config"])

    operation_contract = (
        task.metadata.get("operation")
        if isinstance(task.metadata, dict)
        and isinstance(task.metadata.get("operation"), dict)
        else {}
    )

    semantic_inputs = tuple(
        str(item).strip()
        for item in operation_contract.get("inputs", ())
        if str(item).strip()
    )
    semantic_outputs = tuple(
        str(item).strip()
        for item in operation_contract.get("outputs", ())
        if str(item).strip()
    )

    config_consumed_artifacts = _artifact_refs_for_operation_config(
        operation_metadata.get("config", {})
    )

    consumed_artifact_ids = {ref.artifact_id for ref in config_consumed_artifacts}

    consumed_artifacts = list(config_consumed_artifacts)

    for artifact_id in semantic_inputs:
        if artifact_id in consumed_artifact_ids:
            continue

        consumed_artifacts.append(
            ArtifactReference(
                artifact_id=artifact_id,
            )
        )
        consumed_artifact_ids.add(artifact_id)

    expected_artifact = operation_metadata.get("config", {}).get(
        "artifact_as"
    ) or operation_metadata.get("config", {}).get("save_as")

    produced_artifact_ids: list[str] = []

    if expected_artifact:
        produced_artifact_ids.append(str(expected_artifact))

    for artifact_id in semantic_outputs:
        if artifact_id not in produced_artifact_ids:
            produced_artifact_ids.append(artifact_id)

    produced_artifacts = [
        artifact
        for artifact_id in produced_artifact_ids
        if (
            artifact := _produced_artifact_for_operation(
                operation_id=task.id,
                capability_id=selected_capability,
                artifact_id=artifact_id,
            )
        )
        is not None
    ]

    return PlanningOperation(
        invocation=PlanningCapabilityInvocation(
            capability_id=selected_capability or "",
            arguments=operation_metadata.get("config", {}),
            inputs=[
                InvocationInput(
                    artifact_id=ref.artifact_id,
                    required=ref.required,
                )
                for ref in consumed_artifacts
            ],
            outputs=[
                InvocationOutput(
                    artifact_id=artifact.id,
                    kind=artifact.kind.value,
                )
                for artifact in produced_artifacts
            ],
            execution=InvocationExecutionPolicy(
                timeout_ms=operation_metadata.get("config", {}).get("timeout_ms"),
                retry_count=int(
                    operation_metadata.get("config", {}).get("retries", 0) or 0
                ),
                retry_backoff_ms=int(
                    operation_metadata.get("config", {}).get("retry_backoff_ms", 0) or 0
                ),
                priority=task.priority,
            ),
            consumes=consumed_artifacts,
            produces=produced_artifacts,
            expected_artifact=expected_artifact,
            confidence=1.0,
        ),
        consumes=consumed_artifacts,
        produces=produced_artifacts,
        id=task.id,
        business_task_id=task.id,
        objective=task.description or task.name,
        operation_type=_operation_type_for_category(task.category),
        selected_capability=selected_capability,
        candidate_capabilities=[
            capability.capability_id for capability in task.required_capabilities
        ],
        reasoning=task.description or task.name,
        metadata=operation_metadata,
    )


class PlanningBuilder:
    """
    Converts Business IR into Planning IR.

    Business IR says what work needs to happen.
    Planning IR says what cognitive operations should be performed.

    This builder is intentionally conservative for now:
    it mirrors BusinessTasks into PlanningOperations while preserving
    capability choices and dependency structure.
    """

    def build(self, business_plan: BusinessPlan) -> PlanningPlan:
        operations = [
            planning_operation_from_business_task(task) for task in business_plan.tasks
        ]

        artifacts = [
            artifact for operation in operations for artifact in operation.produces
        ]

        plan = PlanningPlan(
            id=f"planning_{business_plan.id}",
            business_plan_id=business_plan.id,
            operations=operations,
            artifacts=artifacts,
            metadata=PlanningMetadata(
                planner_version=business_plan.metadata.planner_version,
                planning_strategy="business_ir_to_planning_operations",
                confidence=business_plan.metadata.confidence,
                extra={
                    "source_business_goal_id": business_plan.goal.id,
                    "source_business_goal_title": business_plan.goal.title,
                    "source_schema_version": business_plan.schema_version,
                    "business_edges": [
                        edge.model_dump(mode="json") for edge in business_plan.edges
                    ],
                },
            ),
        )

        errors = validate_planning_plan(plan)

        if errors:
            error_text = "; ".join(f"{error.code}: {error.message}" for error in errors)
            raise ValueError(f"Invalid PlanningPlan: {error_text}")

        return plan
