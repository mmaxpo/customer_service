from __future__ import annotations

from typing import Any, Mapping

from app.runtime.objectives.repair.contracts import (
    ObjectiveRepairConstraints,
    ObjectiveRepairRequest,
    ObjectiveRepairSource,
    ObjectiveRepairTarget,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationStatus,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionStatus,
)


OBJECTIVE_REPAIR_REQUEST_VERSION = 1


def build_objective_repair_request_ref(
    *,
    resolution_record_ref: str,
    request_version: int = (
        OBJECTIVE_REPAIR_REQUEST_VERSION
    ),
) -> str:
    normalized_record_ref = str(
        resolution_record_ref
    ).strip()

    if not normalized_record_ref:
        raise ValueError(
            "resolution_record_ref is required"
        )

    if request_version < 1:
        raise ValueError(
            "request_version must be >= 1"
        )

    return (
        "objective-repair:"
        f"{normalized_record_ref}:"
        f"v{request_version}"
    )


class ObjectiveRepairRequestBuilder:
    """
    Convert normalized resolution truth into a generic repair
    request.

    This builder selects what remains unresolved. It does not
    choose retry, wait, replan, escalation, or stop behavior.
    Those decisions belong to a product-owned
    ObjectiveRepairPlanner.
    """

    def build(
        self,
        *,
        resolution_record_ref: str,
        resolution_projection_version: int,
        assessment: ObjectiveResolutionAssessment,
        constraints: ObjectiveRepairConstraints,
        context: Mapping[str, Any] | None = None,
        request_version: int = (
            OBJECTIVE_REPAIR_REQUEST_VERSION
        ),
    ) -> ObjectiveRepairRequest:
        if resolution_projection_version < 1:
            raise ValueError(
                "resolution_projection_version must "
                "be >= 1"
            )

        if assessment.is_terminal:
            raise ValueError(
                "terminal objective resolution cannot "
                "produce a repair request"
            )

        if assessment.status in {
            ObjectiveResolutionStatus.ACHIEVED,
            (
                ObjectiveResolutionStatus
                .INTENTIONALLY_NOT_EXECUTED
            ),
        }:
            raise ValueError(
                "resolved objective cannot produce a "
                "repair request"
            )

        expected_unresolved_refs = tuple(
            operation.operation_ref
            for operation in assessment.operations
            if operation.required
            and operation.status
            in {
                ObjectiveOperationStatus.FAILED,
                ObjectiveOperationStatus.PENDING,
                ObjectiveOperationStatus.UNKNOWN,
            }
        )

        if (
            expected_unresolved_refs
            != assessment.unresolved_operation_refs
        ):
            raise ValueError(
                "resolution unresolved operation refs "
                "do not match operation facts"
            )

        if not expected_unresolved_refs:
            raise ValueError(
                "nonterminal objective has no repairable "
                "unresolved operations"
            )

        targets = tuple(
            ObjectiveRepairTarget(
                operation_ref=(
                    operation.operation_ref
                ),
                operation_type=(
                    operation.operation_type
                ),
                resolution_status=(
                    operation.status
                ),
                required=operation.required,
                reason_code=(
                    operation.reason_code
                ),
                summary=operation.summary,
                source_task_id=(
                    operation.source_task_id
                ),
                verification_ref=(
                    operation.verification_ref
                ),
                evidence_refs=(
                    operation.evidence_refs
                ),
                metadata=dict(
                    operation.metadata or {}
                ),
            )
            for operation in assessment.operations
            if operation.operation_ref
            in set(expected_unresolved_refs)
        )

        return ObjectiveRepairRequest(
            repair_request_ref=(
                build_objective_repair_request_ref(
                    resolution_record_ref=(
                        resolution_record_ref
                    ),
                    request_version=(
                        request_version
                    ),
                )
            ),
            source=ObjectiveRepairSource(
                resolution_record_ref=(
                    resolution_record_ref
                ),
                objective=assessment.objective,
                outcome_ref=(
                    assessment.source.outcome_ref
                ),
                outcome_version=(
                    assessment.source.outcome_version
                ),
                evaluation_ref=(
                    assessment.source.evaluation_ref
                ),
                evaluation_version=(
                    assessment.source
                    .evaluation_version
                ),
                resolution_projection_version=(
                    resolution_projection_version
                ),
                workflow_run_id=(
                    assessment.source.workflow_run_id
                ),
            ),
            resolution_status=assessment.status,
            resolution_reason_code=(
                assessment.reason_code
            ),
            resolution_summary=assessment.summary,
            resolution_confidence=(
                assessment.confidence
            ),
            targets=targets,
            constraints=constraints,
            context=dict(context or {}),
        )


__all__ = [
    "OBJECTIVE_REPAIR_REQUEST_VERSION",
    "ObjectiveRepairRequestBuilder",
    "build_objective_repair_request_ref",
]
