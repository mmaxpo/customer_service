from __future__ import annotations

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


TENANT_ID = "tenant-blocked-candidate"


def _slice_7k_helpers() -> dict[str, Any]:
    """
    Reuse the already proven canonical durable-resolution and
    customer-support source construction helpers from Slice 7K.

    The blocked-candidate scenario changes only aggregation and
    candidate policy. It should not invent a second persistence or
    extraction fixture.
    """

    return runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_mixed_evidence_e2e.py"
    )


class StaticSourceLoader:
    def __init__(
        self,
        *,
        resolution_record_id: UUID,
        source,
    ) -> None:
        self.resolution_record_id = resolution_record_id
        self.source = source
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

        assert resolution_record_id == self.resolution_record_id

        return self.source


def _lifecycle(db) -> ObjectiveLearningLifecycleOperations:
    return ObjectiveLearningLifecycleOperations(
        db=db,
        repository=ObjectiveLearningCandidateRepository(db),
        factory=ObjectiveLearningCandidateFactory(
            policy=ObjectiveLearningCandidatePolicy(
                # Isolate evidence sufficiency as the sole failure.
                minimum_summary_confidence=0.0,
            )
        ),
    )


@pytest.mark.asyncio
async def test_insufficient_evidence_creates_immutable_blocked_candidate():
    """
    One fully valid durable experience is not enough for an
    aggregation requiring an effective sample size of five.

    The resulting blocked candidate must remain stored and visible
    through authenticated lifecycle reads, but it cannot be reviewed,
    approved, projected as an approved insight, or gain execution
    authority.
    """

    helpers = _slice_7k_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_case = helpers["_source_for_case"]

    user_id = uuid4()
    reviewer_id = uuid4()

    base_source = canonical_source()

    async with SessionLocal() as db:
        resolution_record_id = await persist_resolution_parent(
            db,
            user_id=user_id,
            tenant_id=TENANT_ID,
            base_source=base_source,
            case_ref="blocked-single",
            operation_status="achieved",
        )

        # The 7K helper owns a fixture-local tenant constant. Update
        # the returned canonical source to this slice's tenant while
        # preserving every other verified source fact.
        source = source_for_case(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=resolution_record_id,
            case_ref="blocked-single",
            operation_status="achieved",
            confidence=1.0,
        ).model_copy(
            update={
                "tenant_id": TENANT_ID,
            }
        )

        loader = StaticSourceLoader(
            resolution_record_id=resolution_record_id,
            source=source,
        )
        experience_repository = ObjectiveLearningExperienceRepository(db)

        recording = await CustomerSupportObjectiveLearningRecordingService(
            db,
            source_loader=loader,
            repository=experience_repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
            tenant_id=TENANT_ID,
        )

        assert recording.created is True
        assert recording.record.user_id == user_id
        assert recording.record.tenant_id == TENANT_ID
        assert recording.experience.informational_only is True
        assert recording.experience.authorizes_execution is False

        assert loader.calls == [
            {
                "user_id": user_id,
                "resolution_record_id": resolution_record_id,
                "tenant_id": TENANT_ID,
            }
        ]

        experience_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == user_id,
                ObjectiveLearningExperienceRecord.tenant_id == TENANT_ID,
            )
        )

        assert experience_count == 1

        now = datetime.now(timezone.utc) + timedelta(seconds=1)

        summaries = await ObjectiveLearningSummaryService(
            db=db,
            repository=experience_repository,
            aggregation_policy=(
                ObjectiveLearningAggregationPolicy(
                    minimum_effective_sample_size=5.0,
                )
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

        assert summary.total_experiences == 1
        assert summary.unique_resolution_count == 1
        assert summary.effective_sample_size < 5.0
        assert summary.minimum_effective_sample_size == 5.0
        assert summary.evidence_sufficient is False
        assert 0.0 < summary.summary_confidence < 1.0
        assert summary.informational_only is True
        assert summary.authorizes_execution is False

        lifecycle = _lifecycle(db)

        proposal = await lifecycle.propose(
            user_id=user_id,
            aggregation=summary,
            proposed_at=now,
        )

        candidate = proposal.candidate

        assert proposal.created is True
        assert candidate.candidate_version == 1
        assert candidate.status.value == "blocked"
        assert candidate.approval_status.value == "not_required"
        assert candidate.validation_passed is False
        assert candidate.validated_at is None
        assert candidate.reviewed_at is None
        assert candidate.reviewed_by_user_id is None
        assert candidate.review_reason is None
        assert candidate.blocking_reasons == ("evidence_sufficient",)

        checks = {check.code: check.passed for check in candidate.validation_checks}

        assert checks == {
            "evidence_sufficient": False,
            "summary_confidence": True,
            "dimension_evidence_present": True,
            "informational_boundary": True,
        }

        assert candidate.evidence.total_experiences == 1
        assert candidate.evidence.effective_sample_size == summary.effective_sample_size
        assert candidate.evidence.minimum_effective_sample_size == 5.0
        assert candidate.evidence.evidence_sufficient is False
        assert candidate.evidence.aggregation_json == summary.model_dump(mode="json")

        assert candidate.informational_only is True
        assert candidate.affects_ranking is False
        assert candidate.affects_capability_selection is False
        assert candidate.affects_business_plan is False
        assert candidate.selects_provider is False
        assert candidate.authorizes_execution is False
        assert candidate.bypasses_approval is False
        assert candidate.bypasses_verification is False

        latest = await lifecycle.get_latest(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )
        history_before_review = await lifecycle.history(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )

        assert latest == candidate
        assert history_before_review == [candidate]

        # Re-proposing the same evidence is idempotent and must not
        # manufacture another blocked revision.
        repeated = await lifecycle.propose(
            user_id=user_id,
            aggregation=summary,
            proposed_at=(now + timedelta(seconds=1)),
        )

        assert repeated.created is False
        assert repeated.candidate == candidate

        with pytest.raises(
            ValueError,
            match=(
                "Only a pending validated objective learning candidate can be reviewed"
            ),
        ):
            await lifecycle.review(
                user_id=user_id,
                candidate_id=candidate.candidate_id,
                reviewed_by_user_id=reviewer_id,
                request=(
                    ObjectiveLearningCandidateReviewRequest(
                        decision=(ObjectiveLearningReviewDecision.APPROVE),
                        reason=("A blocked candidate must not be approvable."),
                        reviewed_at=(now + timedelta(seconds=2)),
                    )
                ),
            )

        # Failed review must append nothing.
        latest_after_review = await lifecycle.get_latest(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )
        history_after_review = await lifecycle.history(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )

        assert latest_after_review == candidate
        assert history_after_review == [candidate]

        revision_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id
                == candidate.candidate_id,
            )
        )

        assert revision_count == 1

        revision = await db.scalar(
            select(ObjectiveLearningCandidateRevisionRecord).where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id
                == candidate.candidate_id,
            )
        )

        assert revision is not None
        assert revision.version == 1
        assert revision.status == "blocked"
        assert revision.approval_status == "not_required"
        assert revision.validation_passed is False
        assert revision.validated_at is None
        assert revision.reviewed_at is None
        assert revision.reviewed_by_user_id is None
        assert revision.informational_only is True
        assert revision.authorizes_execution is False

        approved_service = ObjectiveLearningApprovedInsightService(
            db=db,
            repository=(ObjectiveLearningCandidateRepository(db)),
        )

        approved = await approved_service.get_approved(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )
        approved_list = await approved_service.list_approved(
            user_id=user_id,
            tenant_id=TENANT_ID,
            objective_namespace=(base_source.objective_namespace),
            objective_type=(base_source.objective_type),
        )

        assert approved is None
        assert approved_list == []
