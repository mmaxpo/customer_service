from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.customer_support_outcome_evaluations import (
    CustomerSupportOutcomeEvaluationRepository,
)
from app.domains.customer_service.repositories.customer_support_outcomes import (
    CustomerSupportOutcomeRepository,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan_loader import (
    CustomerSupportReviewPlanLineageError,
    CustomerSupportReviewPlanLoader,
    CustomerSupportReviewPlanNotFoundError,
)
from app.domains.customer_service.services.support.learning.objective_learning_extraction import (
    CustomerSupportObjectiveLearningSource,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningVersionRef,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairExecutionRepository,
)
from app.runtime.objectives.resolution import (
    ObjectiveResolutionRepository,
)


class CustomerSupportObjectiveLearningSourceLoadError(RuntimeError):
    pass


class CustomerSupportObjectiveLearningSourceNotFoundError(
    CustomerSupportObjectiveLearningSourceLoadError,
    LookupError,
):
    pass


class CustomerSupportObjectiveLearningSourceLineageError(
    CustomerSupportObjectiveLearningSourceLoadError
):
    pass


class CustomerSupportObjectiveLearningSourceLoader:
    """
    Assemble validated JSON-native learning source facts from
    canonical durable customer-support records.

    This product-owned loader is read-only. It does not extract,
    qualify, persist, publish, enqueue, commit, or influence any
    planning or execution decision.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        resolutions: ObjectiveResolutionRepository | None = None,
        outcomes: CustomerSupportOutcomeRepository | None = None,
        evaluations: (CustomerSupportOutcomeEvaluationRepository | None) = None,
        repairs: ObjectiveRepairExecutionRepository | None = None,
        review_plans: CustomerSupportReviewPlanLoader | None = None,
    ) -> None:
        self.db = db
        self.resolutions = resolutions or ObjectiveResolutionRepository(db)
        self.outcomes = outcomes or CustomerSupportOutcomeRepository(db)
        self.evaluations = evaluations or CustomerSupportOutcomeEvaluationRepository(db)
        self.repairs = repairs or ObjectiveRepairExecutionRepository(db)
        self.review_plans = review_plans or CustomerSupportReviewPlanLoader(
            db,
            outcomes=self.outcomes,
        )

    async def load_for_resolution(
        self,
        *,
        user_id: UUID,
        resolution_record_id: UUID,
        tenant_id: str | None = None,
        repair_limit: int = 100,
    ) -> CustomerSupportObjectiveLearningSource:
        normalized_tenant = self._optional_text(tenant_id)

        resolution_record = await self.resolutions.get_for_user(
            user_id=user_id,
            record_id=resolution_record_id,
        )

        if resolution_record is None:
            raise (
                CustomerSupportObjectiveLearningSourceNotFoundError(
                    "Objective resolution record was not found for user"
                )
            )

        record_tenant = self._optional_text(resolution_record.tenant_id)

        if normalized_tenant is not None and record_tenant != normalized_tenant:
            raise (
                CustomerSupportObjectiveLearningSourceNotFoundError(
                    "Objective resolution record was not found for requested tenant"
                )
            )

        try:
            loaded_plan = await self.review_plans.load_for_resolution(
                user_id=user_id,
                resolution_record_id=(resolution_record_id),
            )
        except CustomerSupportReviewPlanNotFoundError as exc:
            raise (
                CustomerSupportObjectiveLearningSourceNotFoundError(str(exc))
            ) from exc
        except CustomerSupportReviewPlanLineageError as exc:
            raise (
                CustomerSupportObjectiveLearningSourceLineageError(str(exc))
            ) from exc

        self._require_equal(
            actual=loaded_plan.resolution_record_id,
            expected=resolution_record.id,
            message=(
                "Canonical review-plan resolution identity "
                "does not match the requested resolution"
            ),
        )

        outcome = await self.outcomes.get_for_user(
            user_id=user_id,
            outcome_id=loaded_plan.support_outcome_id,
        )

        if outcome is None:
            raise (
                CustomerSupportObjectiveLearningSourceNotFoundError(
                    "Canonical customer-support outcome was not found for user"
                )
            )

        source_outcome_id = self._uuid(
            resolution_record.source_outcome_ref,
            "resolution source_outcome_ref",
        )

        self._require_equal(
            actual=outcome.id,
            expected=source_outcome_id,
            message=(
                "Resolution source outcome does not match "
                "the canonical review-plan outcome"
            ),
        )
        self._require_equal(
            actual=outcome.review_plan_id,
            expected=loaded_plan.review_plan_id,
            message=(
                "Support outcome review plan does not match the canonical review plan"
            ),
        )
        self._require_equal(
            actual=outcome.workflow_run_id,
            expected=loaded_plan.workflow_run_id,
            message=(
                "Support outcome workflow run does not match the canonical review plan"
            ),
        )

        evaluation = await self.evaluations.get_by_outcome_version(
            user_id=user_id,
            support_outcome_id=outcome.id,
            evaluation_version=(resolution_record.evaluation_version),
        )

        if evaluation is None:
            raise (
                CustomerSupportObjectiveLearningSourceNotFoundError(
                    "Canonical support outcome evaluation was "
                    "not found for the resolution version"
                )
            )

        source_evaluation_id = self._uuid(
            resolution_record.source_evaluation_ref,
            "resolution source_evaluation_ref",
        )

        self._require_equal(
            actual=evaluation.id,
            expected=source_evaluation_id,
            message=(
                "Resolution source evaluation does not match the canonical evaluation"
            ),
        )
        self._require_equal(
            actual=evaluation.support_outcome_id,
            expected=outcome.id,
            message=("Support evaluation does not reference the canonical outcome"),
        )
        self._require_equal(
            actual=evaluation.review_plan_id,
            expected=outcome.review_plan_id,
            message=(
                "Support evaluation review plan does not match the canonical outcome"
            ),
        )
        self._require_equal(
            actual=evaluation.workflow_run_id,
            expected=outcome.workflow_run_id,
            message=(
                "Support evaluation workflow run does not match the canonical outcome"
            ),
        )

        self._require_objective_lineage(
            resolution=resolution_record,
            outcome=outcome,
        )

        repair_records = await self.repairs.list_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record.id,
            limit=repair_limit,
        )

        repair_snapshots = tuple(
            self._repair_snapshot(
                repair=repair,
                resolution=resolution_record,
                user_id=user_id,
                tenant_id=record_tenant,
            )
            for repair in repair_records
        )

        resolution_snapshot = deepcopy(dict(resolution_record.assessment_json or {}))

        review_plan_snapshot = loaded_plan.review_plan.model_dump(mode="json")
        review_plan_snapshot = {
            "review_plan_id": (loaded_plan.review_plan_id),
            **review_plan_snapshot,
        }

        outcome_snapshot = deepcopy(dict(outcome.outcome_json or {}))

        evaluation_snapshot = self._evaluation_snapshot(
            resolution=resolution_record,
            evaluation=evaluation,
        )

        capability_ids, provider_ids, provider_refs = self._provider_scope(
            review_plan_snapshot
        )

        evidence_refs = self._evidence_refs(
            resolution=resolution_snapshot,
            evaluation=evaluation_snapshot,
        )

        return CustomerSupportObjectiveLearningSource(
            user_id=str(user_id),
            tenant_id=record_tenant,
            objective_namespace=(resolution_record.objective_namespace),
            objective_type=(resolution_record.objective_type),
            objective_ref=(resolution_record.objective_ref),
            objective_version=(resolution_record.objective_version),
            resolution_record_id=str(resolution_record.id),
            resolution=resolution_snapshot,
            review_plan_id=loaded_plan.review_plan_id,
            review_plan=review_plan_snapshot,
            outcome_ref=str(outcome.id),
            outcome_version=outcome.outcome_version,
            outcome=outcome_snapshot,
            evaluation_ref=str(evaluation.id),
            evaluation_version=(evaluation.evaluation_version),
            evaluation=evaluation_snapshot,
            workflow_run_id=str(loaded_plan.workflow_run_id),
            capability_ids=capability_ids,
            provider_ids=provider_ids,
            provider_refs=provider_refs,
            repair_executions=repair_snapshots,
            evidence_refs=evidence_refs,
            versioned_refs=(
                ObjectiveLearningVersionRef(
                    ref="objective_resolution_projection",
                    version=str(resolution_record.projection_version),
                ),
                ObjectiveLearningVersionRef(
                    ref="objective_resolution_assessment",
                    version=str(resolution_record.assessment_schema_version),
                ),
            ),
            metadata={
                "source": ("canonical_durable_customer_support_records"),
                "read_only": True,
                "repair_execution_count": len(repair_snapshots),
            },
        )

    @classmethod
    def _require_objective_lineage(
        cls,
        *,
        resolution,
        outcome,
    ) -> None:
        """
        Verify that the canonical support outcome belongs to the
        exact objective identity represented by the resolution.

        Outcome persistence names the originating objective version
        source_objective_version, while generic resolution persistence
        names it objective_version. The mapping is explicit here.
        """

        comparisons = (
            (
                "objective_namespace",
                outcome.objective_namespace,
                resolution.objective_namespace,
            ),
            (
                "objective_type",
                outcome.objective_type,
                resolution.objective_type,
            ),
            (
                "objective_ref",
                outcome.objective_ref,
                resolution.objective_ref,
            ),
            (
                "objective_version",
                outcome.source_objective_version,
                resolution.objective_version,
            ),
        )

        for field_name, actual, expected in comparisons:
            cls._require_equal(
                actual=actual,
                expected=expected,
                message=(
                    f"Support outcome objective lineage does not match: {field_name}"
                ),
            )

    @classmethod
    def _evaluation_snapshot(
        cls,
        *,
        resolution,
        evaluation,
    ) -> dict[str, Any]:
        return {
            "objective_namespace": (resolution.objective_namespace),
            "objective_type": (resolution.objective_type),
            "objective_ref": (resolution.objective_ref),
            "objective_version": (resolution.objective_version),
            "evaluation_id": str(evaluation.id),
            "support_outcome_id": str(evaluation.support_outcome_id),
            "review_plan_id": (evaluation.review_plan_id),
            "workflow_run_id": str(evaluation.workflow_run_id),
            "evaluation_version": (evaluation.evaluation_version),
            "result": evaluation.result,
            "reason_code": evaluation.reason_code,
            "summary": evaluation.summary,
            "confidence": evaluation.confidence,
            "retryable": evaluation.retryable,
            "achieved_operation_count": (evaluation.achieved_operation_count),
            "failed_operation_count": (evaluation.failed_operation_count),
            "pending_operation_count": (evaluation.pending_operation_count),
            "unknown_operation_count": (evaluation.unknown_operation_count),
            "not_executed_operation_count": (evaluation.not_executed_operation_count),
            "observed_outcome_json": deepcopy(
                dict(evaluation.observed_outcome_json or {})
            ),
            "evidence_json": {"items": deepcopy(list(evaluation.evidence_json or []))},
        }

    @classmethod
    def _repair_snapshot(
        cls,
        *,
        repair,
        resolution,
        user_id: UUID,
        tenant_id: str | None,
    ) -> dict[str, Any]:
        cls._require_equal(
            actual=repair.user_id,
            expected=user_id,
            message=("Repair execution owner does not match the requested user"),
        )
        cls._require_equal(
            actual=repair.resolution_record_id,
            expected=resolution.id,
            message=("Repair execution does not reference the requested resolution"),
        )

        repair_tenant = cls._optional_text(repair.tenant_id)

        if repair_tenant != tenant_id:
            raise (
                CustomerSupportObjectiveLearningSourceLineageError(
                    "Repair execution tenant does not match the objective resolution"
                )
            )

        for field_name in (
            "objective_namespace",
            "objective_type",
            "objective_ref",
            "objective_version",
        ):
            cls._require_equal(
                actual=getattr(repair, field_name),
                expected=getattr(
                    resolution,
                    field_name,
                ),
                message=(
                    f"Repair execution objective lineage does not match: {field_name}"
                ),
            )

        return {
            "id": str(repair.id),
            "repair_execution_id": str(repair.id),
            "source_event_id": str(repair.source_event_id),
            "resolution_record_id": str(repair.resolution_record_id),
            "repair_request_ref": (repair.repair_request_ref),
            "repair_request_version": (repair.repair_request_version),
            "repair_plan_version": (repair.repair_plan_version),
            "planner_ref": repair.planner_ref,
            "planner_policy_version": (repair.planner_policy_version),
            "controlling_disposition": (repair.controlling_disposition),
            "status": repair.status,
            "attempt_number": (repair.attempt_number),
            "requires_human_approval": (repair.requires_human_approval),
            "automatic_execution_allowed": (repair.automatic_execution_allowed),
            "request_json": deepcopy(dict(repair.request_json or {})),
            "plan_json": deepcopy(dict(repair.plan_json or {})),
            "workflow_json": (
                deepcopy(dict(repair.workflow_json))
                if repair.workflow_json is not None
                else None
            ),
            "workflow_job_id": (
                str(repair.workflow_job_id)
                if repair.workflow_job_id is not None
                else None
            ),
            "workflow_run_id": (cls._optional_text(repair.workflow_run_id)),
            "result_json": (
                deepcopy(dict(repair.result_json))
                if repair.result_json is not None
                else None
            ),
            "failure_code": (repair.failure_code),
            "failure_message": (repair.failure_message),
            "created_at": cls._isoformat(repair.created_at),
            "launched_at": cls._isoformat(repair.launched_at),
            "completed_at": cls._isoformat(repair.completed_at),
        }

    @classmethod
    def _provider_scope(
        cls,
        review_plan: dict[str, Any],
    ) -> tuple[
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        """
        Return only capability and provider identities explicitly
        retained by the canonical review-plan snapshot.

        Current support review plans retain one top-level provider,
        but their operation contract does not retain semantic
        capability IDs, provider IDs, or provider executor refs.
        Those fields therefore remain empty unless a future
        version explicitly persists them.
        """

        capability_ids: list[str] = []
        provider_ids: list[str] = []
        provider_refs: list[str] = []

        cls._append_text(
            provider_ids,
            review_plan.get("provider"),
            lowercase=True,
        )

        operations = review_plan.get("operations")

        if not isinstance(operations, list):
            operations = []

        for operation in operations:
            if not isinstance(operation, dict):
                continue

            cls._append_text(
                capability_ids,
                operation.get("capability_id"),
                lowercase=True,
            )
            cls._append_text(
                provider_ids,
                operation.get("provider_id"),
                lowercase=True,
            )
            cls._append_text(
                provider_refs,
                operation.get("provider_ref"),
                lowercase=True,
            )

        return (
            tuple(capability_ids),
            tuple(provider_ids),
            tuple(provider_refs),
        )

    @classmethod
    def _evidence_refs(
        cls,
        *,
        resolution: dict[str, Any],
        evaluation: dict[str, Any],
    ) -> tuple[str, ...]:
        refs: list[str] = []

        raw_refs = resolution.get("evidence_refs")

        if isinstance(raw_refs, list):
            for value in raw_refs:
                cls._append_text(
                    refs,
                    value,
                    lowercase=False,
                )

        operations = resolution.get("operations")

        if isinstance(operations, list):
            for operation in operations:
                if not isinstance(
                    operation,
                    dict,
                ):
                    continue

                cls._append_text(
                    refs,
                    operation.get("verification_ref"),
                    lowercase=False,
                )

        evidence = evaluation.get("evidence_json")

        if isinstance(evidence, dict):
            items = evidence.get("items")
        else:
            items = evidence

        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue

                cls._append_text(
                    refs,
                    item.get("evidence_ref"),
                    lowercase=False,
                )

        return tuple(refs)

    @staticmethod
    def _append_text(
        values: list[str],
        value: Any,
        *,
        lowercase: bool,
    ) -> None:
        if value is None:
            return

        normalized = str(value).strip()

        if not normalized:
            return

        if lowercase:
            normalized = normalized.lower()

        if normalized not in values:
            values.append(normalized)

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _uuid(
        value: Any,
        field_name: str,
    ) -> UUID:
        try:
            return UUID(str(value))
        except (
            TypeError,
            ValueError,
            AttributeError,
        ) as exc:
            raise (
                CustomerSupportObjectiveLearningSourceLineageError(
                    f"{field_name} must be a valid UUID"
                )
            ) from exc

    @staticmethod
    def _isoformat(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        isoformat = getattr(
            value,
            "isoformat",
            None,
        )

        if callable(isoformat):
            return str(isoformat())

        return str(value)

    @staticmethod
    def _require_equal(
        *,
        actual: Any,
        expected: Any,
        message: str,
    ) -> None:
        if str(actual) != str(expected):
            raise (CustomerSupportObjectiveLearningSourceLineageError(message))


__all__ = [
    "CustomerSupportObjectiveLearningSourceLineageError",
    "CustomerSupportObjectiveLearningSourceLoadError",
    "CustomerSupportObjectiveLearningSourceLoader",
    "CustomerSupportObjectiveLearningSourceNotFoundError",
]
