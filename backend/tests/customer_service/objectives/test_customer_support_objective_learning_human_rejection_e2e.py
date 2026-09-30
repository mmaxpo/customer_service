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


TENANT_ID = "tenant-human-rejection"
REJECTION_REASON = (
    "Evidence is valid, but this guidance is not suitable "
    "for future customer-support planning."
)


def _slice_7k_helpers() -> dict[str, Any]:
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
                minimum_summary_confidence=0.0,
            )
        ),
    )


@pytest.mark.asyncio
async def test_human_rejection_appends_revision_and_never_exposes_approved_insight():
    """
    Valid evidence may produce a reviewable candidate, but the human
    reviewer retains final control.

    Rejection must append an immutable second revision, preserve the
    original validated revision, prevent repeated review, and exclude
    the candidate from approved advisory retrieval.
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
            case_ref="human-rejection",
            operation_status="achieved",
        )

        source = source_for_case(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=resolution_record_id,
            case_ref="human-rejection",
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

        now = datetime.now(timezone.utc) + timedelta(seconds=1)

        summaries = await ObjectiveLearningSummaryService(
            db=db,
            repository=experience_repository,
            aggregation_policy=(
                ObjectiveLearningAggregationPolicy(
                    minimum_effective_sample_size=0.5,
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

        assert summary.evidence_sufficient is True
        assert summary.total_experiences == 1
        assert summary.informational_only is True
        assert summary.authorizes_execution is False

        lifecycle = _lifecycle(db)

        proposal = await lifecycle.propose(
            user_id=user_id,
            aggregation=summary,
            proposed_at=now,
        )

        version_one = proposal.candidate

        assert proposal.created is True
        assert version_one.candidate_version == 1
        assert version_one.status.value == "validated"
        assert version_one.approval_status.value == "pending"
        assert version_one.validation_passed is True
        assert version_one.validated_at is not None
        assert version_one.reviewed_at is None
        assert version_one.reviewed_by_user_id is None
        assert version_one.review_reason is None
        assert version_one.blocking_reasons == ("explicit_approval_required",)

        reviewed_at = now + timedelta(seconds=1)

        rejected = await lifecycle.review(
            user_id=user_id,
            candidate_id=version_one.candidate_id,
            reviewed_by_user_id=reviewer_id,
            request=(
                ObjectiveLearningCandidateReviewRequest(
                    decision=(ObjectiveLearningReviewDecision.REJECT),
                    reason=f"  {REJECTION_REASON}  ",
                    reviewed_at=reviewed_at,
                )
            ),
        )

        assert rejected is not None
        assert rejected.candidate_id == version_one.candidate_id
        assert rejected.candidate_version == 2
        assert rejected.status.value == "rejected"
        assert rejected.approval_status.value == "rejected"
        assert rejected.validation_passed is True
        assert rejected.validated_at == version_one.validated_at
        assert rejected.reviewed_at == reviewed_at
        assert rejected.reviewed_by_user_id == reviewer_id
        assert rejected.review_reason == REJECTION_REASON
        assert rejected.blocking_reasons == ("approval_rejected",)

        assert rejected.evidence == version_one.evidence
        assert rejected.validation_checks == version_one.validation_checks
        assert rejected.proposed_at == version_one.proposed_at

        assert rejected.informational_only is True
        assert rejected.affects_ranking is False
        assert rejected.affects_capability_selection is False
        assert rejected.affects_business_plan is False
        assert rejected.selects_provider is False
        assert rejected.authorizes_execution is False
        assert rejected.bypasses_approval is False
        assert rejected.bypasses_verification is False

        repository = ObjectiveLearningCandidateRepository(db)

        version_one_row = await repository.get_revision_for_user(
            user_id=user_id,
            candidate_id=version_one.candidate_id,
            version=1,
        )
        version_two_row = await repository.get_revision_for_user(
            user_id=user_id,
            candidate_id=version_one.candidate_id,
            version=2,
        )

        assert version_one_row is not None
        assert version_two_row is not None

        persisted_version_one = repository.deserialize(version_one_row)
        persisted_version_two = repository.deserialize(version_two_row)

        # The original validated revision remains unchanged.
        assert persisted_version_one == version_one
        assert persisted_version_one.candidate_version == 1
        assert persisted_version_one.status.value == "validated"
        assert persisted_version_one.approval_status.value == "pending"
        assert persisted_version_one.reviewed_at is None
        assert persisted_version_one.reviewed_by_user_id is None
        assert persisted_version_one.review_reason is None
        assert persisted_version_one.blocking_reasons == ("explicit_approval_required",)

        assert persisted_version_two == rejected

        history = await lifecycle.history(
            user_id=user_id,
            candidate_id=version_one.candidate_id,
        )
        latest = await lifecycle.get_latest(
            user_id=user_id,
            candidate_id=version_one.candidate_id,
        )

        assert history == [
            version_one,
            rejected,
        ]
        assert latest == rejected

        revision_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id
                == version_one.candidate_id,
            )
        )

        assert revision_count == 2

        with pytest.raises(
            ValueError,
            match=(
                "Only a pending validated objective learning candidate can be reviewed"
            ),
        ):
            await lifecycle.review(
                user_id=user_id,
                candidate_id=version_one.candidate_id,
                reviewed_by_user_id=reviewer_id,
                request=(
                    ObjectiveLearningCandidateReviewRequest(
                        decision=(ObjectiveLearningReviewDecision.APPROVE),
                        reason=("A rejected candidate cannot be reviewed again."),
                        reviewed_at=(reviewed_at + timedelta(seconds=1)),
                    )
                ),
            )

        # Repeated review failure must append nothing.
        history_after_repeat = await lifecycle.history(
            user_id=user_id,
            candidate_id=version_one.candidate_id,
        )

        assert history_after_repeat == [
            version_one,
            rejected,
        ]

        revision_count_after_repeat = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id
                == version_one.candidate_id,
            )
        )

        assert revision_count_after_repeat == 2

        approved_service = ObjectiveLearningApprovedInsightService(
            db=db,
            repository=repository,
        )

        approved = await approved_service.get_approved(
            user_id=user_id,
            candidate_id=version_one.candidate_id,
        )
        approved_list = await approved_service.list_approved(
            user_id=user_id,
            tenant_id=TENANT_ID,
            objective_namespace=(base_source.objective_namespace),
            objective_type=(base_source.objective_type),
        )

        assert approved is None
        assert approved_list == []
