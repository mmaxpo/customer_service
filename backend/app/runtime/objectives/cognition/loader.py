from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveRepairExecutionRecord,
    ObjectiveResolutionRecord,
)
from app.runtime.objectives.cognition.contracts import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveProvenance,
    ObjectiveRepairCognitiveFact,
    ObjectiveResolutionCognitiveFact,
)
from app.runtime.objectives.repair.repository import (
    ObjectiveRepairExecutionRepository,
)
from app.runtime.objectives.resolution.repository import (
    ObjectiveResolutionRepository,
    normalize_resolution_user_id,
)


class ObjectiveCognitiveContextLoader:
    """
    Load current durable objective facts for cognitive consumers.

    Responsibilities:
    - enforce authenticated user scope through repositories;
    - select the latest durable objective resolution;
    - select the latest repair for that exact resolution;
    - normalize records into immutable product-neutral contracts.

    Non-responsibilities:
    - no planning decisions;
    - no capability selection;
    - no workflow launch;
    - no repair transition;
    - no learning persistence;
    - no transaction commit.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        resolution_repository: (
            ObjectiveResolutionRepository | None
        ) = None,
        repair_repository: (
            ObjectiveRepairExecutionRepository | None
        ) = None,
    ) -> None:
        self.db = db
        self.resolutions = (
            resolution_repository
            or ObjectiveResolutionRepository(db)
        )
        self.repairs = (
            repair_repository
            or ObjectiveRepairExecutionRepository(db)
        )

    async def load_for_objective(
        self,
        *,
        user_id: UUID | str,
        objective_namespace: str,
        objective_ref: str,
        tenant_id: str | None = None,
    ) -> ObjectiveCognitiveContext:
        normalized_user_id = (
            normalize_resolution_user_id(user_id)
        )
        normalized_namespace = self._required_text(
            objective_namespace,
            "objective_namespace",
        ).lower()
        normalized_ref = self._required_text(
            objective_ref,
            "objective_ref",
        )
        normalized_tenant = self._optional_text(
            tenant_id
        )

        identity = ObjectiveCognitiveIdentity(
            namespace=normalized_namespace,
            objective_ref=normalized_ref,
        )

        resolution = await (
            self.resolutions
            .get_latest_for_objective(
                user_id=normalized_user_id,
                objective_namespace=(
                    normalized_namespace
                ),
                objective_ref=normalized_ref,
            )
        )

        if resolution is None:
            return self._absent(identity)

        if (
            normalized_tenant is not None
            and self._optional_text(
                resolution.tenant_id
            )
            != normalized_tenant
        ):
            return self._absent(identity)

        resolution_fact = (
            self._resolution_fact(resolution)
        )

        repair = await (
            self.repairs
            .get_latest_for_resolution(
                user_id=normalized_user_id,
                resolution_record_id=resolution.id,
            )
        )

        repair_fact = (
            self._repair_fact(repair)
            if repair is not None
            else None
        )

        resolved_identity = (
            ObjectiveCognitiveIdentity(
                namespace=(
                    resolution.objective_namespace
                ),
                objective_ref=(
                    resolution.objective_ref
                ),
                objective_type=(
                    resolution.objective_type
                ),
                objective_version=(
                    resolution.objective_version
                ),
            )
        )

        return ObjectiveCognitiveContext(
            present=True,
            identity=resolved_identity,
            resolution=resolution_fact,
            latest_repair=repair_fact,
            provenance=(
                ObjectiveCognitiveProvenance(
                    resolution_record_id=(
                        resolution.id
                    ),
                    repair_execution_id=(
                        repair.id
                        if repair is not None
                        else None
                    ),
                )
            ),
            metadata={
                "tenant_scope_requested": (
                    normalized_tenant is not None
                ),
            },
        )

    @staticmethod
    def _absent(
        identity: ObjectiveCognitiveIdentity,
    ) -> ObjectiveCognitiveContext:
        return ObjectiveCognitiveContext(
            present=False,
            identity=identity,
            provenance=(
                ObjectiveCognitiveProvenance()
            ),
        )

    @classmethod
    def _resolution_fact(
        cls,
        record: ObjectiveResolutionRecord,
    ) -> ObjectiveResolutionCognitiveFact:
        assessment = deepcopy(
            dict(record.assessment_json or {})
        )

        return ObjectiveResolutionCognitiveFact(
            resolution_record_id=record.id,
            source_event_id=record.source_event_id,
            tenant_id=record.tenant_id,
            workflow_run_id=record.workflow_run_id,
            status=record.status,
            reason_code=record.reason_code,
            summary=record.summary,
            confidence=record.confidence,
            is_terminal=record.is_terminal,
            source_outcome_ref=(
                record.source_outcome_ref
            ),
            outcome_version=record.outcome_version,
            source_evaluation_ref=(
                record.source_evaluation_ref
            ),
            evaluation_version=(
                record.evaluation_version
            ),
            projection_version=(
                record.projection_version
            ),
            operation_count=(
                record.operation_count
            ),
            achieved_operation_count=(
                record.achieved_operation_count
            ),
            unresolved_operation_count=(
                record.unresolved_operation_count
            ),
            failed_operation_count=(
                record.failed_operation_count
            ),
            pending_operation_count=(
                record.pending_operation_count
            ),
            unknown_operation_count=(
                record.unknown_operation_count
            ),
            not_executed_operation_count=(
                record
                .not_executed_operation_count
            ),
            unresolved_operation_refs=(
                cls._string_tuple(
                    assessment.get(
                        "unresolved_operation_refs"
                    )
                )
            ),
            failed_operation_refs=(
                cls._string_tuple(
                    assessment.get(
                        "failed_operation_refs"
                    )
                )
            ),
            pending_operation_refs=(
                cls._string_tuple(
                    assessment.get(
                        "pending_operation_refs"
                    )
                )
            ),
            unknown_operation_refs=(
                cls._string_tuple(
                    assessment.get(
                        "unknown_operation_refs"
                    )
                )
            ),
            not_executed_operation_refs=(
                cls._string_tuple(
                    assessment.get(
                        "not_executed_operation_refs"
                    )
                )
            ),
            created_at=record.created_at,
        )

    @classmethod
    def _repair_fact(
        cls,
        record: ObjectiveRepairExecutionRecord,
    ) -> ObjectiveRepairCognitiveFact:
        result = deepcopy(
            dict(record.result_json or {})
        )
        runtime_meta = cls._dict(
            result.get("meta")
        )
        final_state = cls._dict(
            runtime_meta.get("final_state")
        )
        variables = cls._dict(
            final_state.get("vars")
        )
        repair_result = cls._dict(
            variables.get("repair_result")
        )

        return ObjectiveRepairCognitiveFact(
            repair_execution_id=record.id,
            resolution_record_id=(
                record.resolution_record_id
            ),
            source_event_id=record.source_event_id,
            status=record.status,
            attempt_number=record.attempt_number,
            repair_request_ref=(
                record.repair_request_ref
            ),
            repair_request_version=(
                record.repair_request_version
            ),
            planner_ref=record.planner_ref,
            planner_policy_version=(
                record.planner_policy_version
            ),
            disposition=record.disposition,
            reason_code=record.reason_code,
            summary=record.summary,
            confidence=record.confidence,
            automatic_execution_allowed=(
                record
                .automatic_execution_allowed
            ),
            human_approval_required=(
                record.human_approval_required
            ),
            workflow_job_id=record.workflow_job_id,
            workflow_run_id=record.workflow_run_id,
            runtime_status=cls._optional_text(
                runtime_meta.get("status")
            ),
            repair_result_status=(
                cls._optional_text(
                    repair_result.get("status")
                )
            ),
            failure_code=record.failure_code,
            failure_message=record.failure_message,
            created_at=record.created_at,
            completed_at=record.completed_at,
        )

    @staticmethod
    def _dict(value: Any) -> dict:
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _string_tuple(
        value: Any,
    ) -> tuple[str, ...]:
        if not isinstance(
            value,
            (list, tuple, set),
        ):
            return ()

        return tuple(
            text
            for item in value
            if (
                text := str(item).strip()
            )
        )

    @staticmethod
    def _required_text(
        value: Any,
        field_name: str,
    ) -> str:
        normalized = str(value or "").strip()

        if not normalized:
            raise ValueError(
                f"{field_name} is required"
            )

        return normalized

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None


__all__ = [
    "ObjectiveCognitiveContextLoader",
]
