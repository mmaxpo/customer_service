from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import runpy
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
    ObjectiveLearningExperienceRecord,
)
from app.platform.events.event_store import PlatformEventStore
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingService,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningAggregationPolicy,
    ObjectiveLearningApprovedInsightService,
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateRepository,
    ObjectiveLearningCandidateReviewRequest,
    ObjectiveLearningExperienceRepository,
    ObjectiveLearningLifecycleOperations,
    ObjectiveLearningReviewDecision,
    ObjectiveLearningSummaryService,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionService,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


TENANT_ID = "tenant-mixed-evidence"

STATUS_MATRIX = (
    ("achieved-1", "achieved", 1.0),
    ("achieved-2", "achieved", 0.95),
    ("achieved-3", "achieved", 0.90),
    ("failed-1", "failed", 0.85),
    ("failed-2", "failed", 0.80),
    ("pending-1", "pending", 0.75),
)


def _canonical_source():
    namespace = runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_recording.py"
    )

    return namespace["_source"]()


class SourceMapLoader:
    def __init__(self, sources: dict[UUID, Any]) -> None:
        self.sources = sources
        self.calls: list[dict[str, Any]] = []

    async def load_for_resolution(
        self,
        *,
        user_id,
        resolution_record_id,
        tenant_id=None,
    ):
        self.calls.append(
            {
                "user_id": user_id,
                "resolution_record_id": resolution_record_id,
                "tenant_id": tenant_id,
            }
        )

        return self.sources[resolution_record_id]


def _replace_objective_identity(
    payload: Any,
    *,
    objective_ref: str,
) -> Any:
    """
    Update objective_ref wherever the canonical snapshots retain it,
    without inventing a new snapshot shape.
    """

    if isinstance(payload, dict):
        updated = {}

        for key, value in payload.items():
            if key == "objective_ref":
                updated[key] = objective_ref
            else:
                updated[key] = _replace_objective_identity(
                    value,
                    objective_ref=objective_ref,
                )

        return updated

    if isinstance(payload, list):
        return [
            _replace_objective_identity(
                item,
                objective_ref=objective_ref,
            )
            for item in payload
        ]

    return payload


def _resolution_operations(
    resolution: dict[str, Any],
) -> list[dict[str, Any]]:
    operations = resolution.get("operations")

    if not isinstance(operations, list):
        raise AssertionError("Canonical resolution fixture must expose operations")

    if not operations:
        raise AssertionError("Canonical resolution fixture must contain an operation")

    return operations


def _source_for_case(
    *,
    base_source,
    user_id: UUID,
    resolution_record_id: UUID,
    case_ref: str,
    operation_status: str,
    confidence: float,
):
    objective_ref = f"mixed-evidence-{case_ref}"
    outcome_ref = f"outcome-{case_ref}"
    evaluation_ref = f"evaluation-{case_ref}"
    workflow_run_id = f"workflow-{case_ref}"

    resolution = _replace_objective_identity(
        deepcopy(base_source.resolution),
        objective_ref=objective_ref,
    )
    outcome = _replace_objective_identity(
        deepcopy(base_source.outcome),
        objective_ref=objective_ref,
    )
    evaluation = _replace_objective_identity(
        deepcopy(base_source.evaluation),
        objective_ref=objective_ref,
    )
    review_plan = deepcopy(base_source.review_plan)

    operations = _resolution_operations(resolution)

    # The canonical fixture contains multiple operations. Normalize
    # every operation first so each case represents exactly one
    # intended outcome rather than inheriting unrelated fixture
    # failures.
    for operation in operations:
        operation["status"] = "achieved"
        operation["resolution_status"] = "achieved"
        operation["reason_code"] = "mixed_evidence_achieved"

    if operation_status != "achieved":
        operations[0]["status"] = operation_status
        operations[0]["resolution_status"] = operation_status
        operations[0]["reason_code"] = f"mixed_evidence_{operation_status}"

    evaluation["confidence"] = confidence

    if isinstance(
        evaluation.get("result"),
        dict,
    ):
        evaluation["result"]["confidence"] = confidence

    return base_source.model_copy(
        update={
            "user_id": str(user_id),
            "tenant_id": TENANT_ID,
            "objective_ref": objective_ref,
            "resolution_record_id": str(resolution_record_id),
            "resolution": resolution,
            "review_plan_id": objective_ref,
            "review_plan": review_plan,
            "outcome_ref": outcome_ref,
            "outcome": outcome,
            "evaluation_ref": evaluation_ref,
            "evaluation": evaluation,
            "workflow_run_id": workflow_run_id,
        }
    )


async def _persist_resolution_parent(
    db,
    *,
    user_id: UUID,
    tenant_id: str,
    base_source,
    case_ref: str,
    operation_status: str,
) -> UUID:
    objective_ref = f"mixed-evidence-{case_ref}"
    outcome_ref = f"outcome-{case_ref}"
    evaluation_ref = f"evaluation-{case_ref}"
    workflow_run_id = f"workflow-{case_ref}"

    source_event = await PlatformEventStore(db).append(
        user_id=user_id,
        event_type=("customer_service.support.outcome.evaluated"),
        source="test.slice_7k",
        payload={
            "case_ref": case_ref,
            "operation_status": operation_status,
        },
        meta={
            "slice": "7k",
            "tenant_id": tenant_id,
            "informational_only": True,
        },
        commit=True,
    )

    if operation_status == "achieved":
        resolution_status = ObjectiveResolutionStatus.ACHIEVED
        operation_enum = ObjectiveOperationStatus.ACHIEVED
        terminal = True
    elif operation_status == "failed":
        resolution_status = ObjectiveResolutionStatus.FAILED
        operation_enum = ObjectiveOperationStatus.FAILED
        terminal = True
    else:
        resolution_status = ObjectiveResolutionStatus.PROGRESSING
        operation_enum = ObjectiveOperationStatus.PENDING
        terminal = False

    assessment = ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace=base_source.objective_namespace,
            objective_type=base_source.objective_type,
            objective_ref=objective_ref,
            objective_version=base_source.objective_version,
        ),
        source=ObjectiveResolutionSource(
            outcome_ref=outcome_ref,
            outcome_version=1,
            evaluation_ref=evaluation_ref,
            evaluation_version=1,
            workflow_run_id=workflow_run_id,
        ),
        status=resolution_status,
        reason_code=f"mixed_evidence_{operation_status}",
        summary=(
            f"Durable customer-support resolution for mixed-evidence case {case_ref}."
        ),
        confidence=1.0,
        is_terminal=terminal,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="verified-support-operation",
                operation_type="customer_support_resolution",
                status=operation_enum,
                required=True,
                reason_code=(f"mixed_evidence_{operation_status}"),
                summary=(f"Observed operation status is {operation_status}."),
                evidence_refs=tuple(base_source.evidence_refs),
            ),
        ),
        metadata={
            "slice": "7k",
            "case_ref": case_ref,
            "operation_status": operation_status,
            "informational_only": True,
            "authorizes_execution": False,
        },
    )

    write = await ObjectiveResolutionService(db).record_assessment(
        source_event_id=source_event.id,
        user_id=user_id,
        tenant_id=tenant_id,
        assessment=assessment,
        projection_version=1,
    )

    assert write.created is True
    assert write.record.user_id == user_id
    assert write.record.tenant_id == tenant_id

    return write.record.id


def _dimension(summary, key: str):
    return next(item for item in summary.dimensions if item.key == key)


def _lifecycle(db):
    return ObjectiveLearningLifecycleOperations(
        db=db,
        repository=ObjectiveLearningCandidateRepository(db),
        factory=ObjectiveLearningCandidateFactory(
            policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
        ),
    )


@pytest.mark.asyncio
async def test_mixed_evidence_remains_visible_and_advisory():
    """
    Three achieved, two failed, and one pending durable outcomes
    converge into one exact-scope aggregation.

    The generic learning runtime must preserve structural conflict
    without interpreting a dominant value as an instruction or
    claiming universal success.
    """

    user_id = uuid4()
    reviewer_id = uuid4()
    base_source = _canonical_source()

    sources: dict[UUID, Any] = {}

    async with SessionLocal() as db:
        for (
            case_ref,
            operation_status,
            confidence,
        ) in STATUS_MATRIX:
            resolution_record_id = await _persist_resolution_parent(
                db,
                user_id=user_id,
                tenant_id=TENANT_ID,
                base_source=base_source,
                case_ref=case_ref,
                operation_status=operation_status,
            )

            sources[resolution_record_id] = _source_for_case(
                base_source=base_source,
                user_id=user_id,
                resolution_record_id=(resolution_record_id),
                case_ref=case_ref,
                operation_status=(operation_status),
                confidence=confidence,
            )

        loader = SourceMapLoader(sources)
        repository = ObjectiveLearningExperienceRepository(db)
        recording_service = CustomerSupportObjectiveLearningRecordingService(
            db,
            source_loader=loader,
            repository=repository,
        )

        recorded = []

        for resolution_record_id in sources:
            result = await recording_service.record_for_resolution(
                user_id=user_id,
                resolution_record_id=(resolution_record_id),
                tenant_id=TENANT_ID,
            )

            assert result.created is True
            assert result.record.user_id == user_id
            assert result.record.tenant_id == TENANT_ID
            assert result.experience.informational_only is True
            assert result.experience.authorizes_execution is False

            recorded.append(result)

        assert len(recorded) == 6
        assert len(loader.calls) == 6

        durable_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == user_id,
                ObjectiveLearningExperienceRecord.tenant_id == TENANT_ID,
            )
        )

        assert durable_count == 6

        now = datetime.now(timezone.utc) + timedelta(seconds=1)

        summaries = await ObjectiveLearningSummaryService(
            db=db,
            repository=repository,
            aggregation_policy=(
                ObjectiveLearningAggregationPolicy(minimum_effective_sample_size=3.0)
            ),
        ).summarize(
            user_id=user_id,
            window_hours=24,
            tenant_id=TENANT_ID,
            objective_namespace=(base_source.objective_namespace),
            objective_type=base_source.objective_type,
            now=now,
        )

        assert len(summaries) == 1

        summary = summaries[0]

        assert summary.total_experiences == 6
        assert summary.unique_objective_count == 6
        assert summary.unique_resolution_count == 6
        assert summary.unique_outcome_count == 6
        assert summary.unique_evaluation_count == 6
        assert summary.unique_workflow_run_count == 6

        assert summary.evidence.experience_count == 6
        assert summary.evidence.experiences_with_evidence == 6
        assert summary.evidence.coverage == 1.0

        assert summary.effective_sample_size > 3.0
        assert summary.evidence_sufficient is True
        assert 0.0 < summary.summary_confidence <= 1.0

        failure_pattern = _dimension(
            summary,
            "failure_pattern",
        )

        # Two failed and one pending experience expose a failure
        # pattern. Achieved experiences correctly omit it.
        assert failure_pattern.occurrence_count == 3
        assert failure_pattern.experience_count == 6
        assert failure_pattern.experience_coverage == 0.5

        # Failed and pending payloads are not collapsed into one
        # universal interpretation.
        assert failure_pattern.distinct_value_count >= 2
        assert (
            failure_pattern.dominant_value_occurrences
            < failure_pattern.occurrence_count
        )
        assert failure_pattern.value_consistency_ratio < 1.0

        required_evidence = _dimension(
            summary,
            "required_evidence",
        )

        assert required_evidence.occurrence_count == 6
        assert required_evidence.experience_coverage == 1.0
        assert required_evidence.distinct_value_count == 6

        plan_structure = _dimension(
            summary,
            "plan_structure",
        )

        assert plan_structure.occurrence_count == 6
        assert plan_structure.experience_coverage == 1.0

        candidate_result = await _lifecycle(db).propose(
            user_id=user_id,
            aggregation=summary,
            proposed_at=now,
        )

        candidate = candidate_result.candidate

        assert candidate_result.created is True
        assert candidate.candidate_version == 1
        assert candidate.status.value == "validated"
        assert candidate.approval_status.value == "pending"
        assert candidate.validation_passed is True
        assert candidate.evidence.total_experiences == 6
        assert candidate.evidence.evidence_sufficient is True
        assert candidate.evidence.summary_confidence == summary.summary_confidence
        assert candidate.evidence.aggregation_json == summary.model_dump(mode="json")
        assert candidate.informational_only is True
        assert candidate.authorizes_execution is False
        assert candidate.affects_ranking is False
        assert candidate.affects_capability_selection is False
        assert candidate.selects_provider is False

        approved = await _lifecycle(db).review(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
            reviewed_by_user_id=reviewer_id,
            request=(
                ObjectiveLearningCandidateReviewRequest(
                    decision=(ObjectiveLearningReviewDecision.APPROVE),
                    reason=(
                        "Accept the mixed evidence as an "
                        "advisory record; do not interpret "
                        "it as universal success."
                    ),
                    reviewed_at=(now + timedelta(seconds=1)),
                )
            ),
        )

        assert approved is not None
        assert approved.candidate_version == 2
        assert approved.status.value == "approved"
        assert approved.approval_status.value == "approved"

        insight = await ObjectiveLearningApprovedInsightService(
            db=db,
            repository=(ObjectiveLearningCandidateRepository(db)),
        ).get_approved(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )

        assert insight is not None
        assert insight.total_experiences == 6
        assert insight.evidence_sufficient is True
        assert insight.summary_confidence == summary.summary_confidence
        assert insight.evidence == summary.evidence
        assert insight.dimensions == summary.dimensions

        projected_failure_pattern = _dimension(
            insight,
            "failure_pattern",
        )

        assert projected_failure_pattern == failure_pattern
        assert projected_failure_pattern.value_consistency_ratio < 1.0

        assert "mixed evidence" in insight.recommended_review.lower()
        assert "universal success" in insight.recommended_review.lower()

        assert insight.informational_only is True
        assert insight.affects_ranking is False
        assert insight.affects_capability_selection is False
        assert insight.affects_business_plan is False
        assert insight.selects_provider is False
        assert insight.authorizes_execution is False
        assert insight.bypasses_approval is False
        assert insight.bypasses_verification is False

        revision_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id
                == candidate.candidate_id,
            )
        )

        assert revision_count == 2
