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
from app.platform.events.event_store import PlatformEventStore
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingService,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningAggregation,
    ObjectiveLearningAggregationPolicy,
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


def _canonical_source():
    namespace = runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_recording.py"
    )

    return namespace["_source"]()


class StaticCanonicalSourceLoader:
    def __init__(self, source) -> None:
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

        return self.source


class FailAfterExperienceFlushRepository:
    """
    Simulate worker/process failure after the experience INSERT has
    flushed but before the recording service commits its transaction.
    """

    def __init__(self, db) -> None:
        self.delegate = ObjectiveLearningExperienceRepository(db)
        self.calls = 0

    async def record(self, **kwargs):
        self.calls += 1

        await self.delegate.record(**kwargs)

        raise RuntimeError("simulated crash after experience flush")


class FailOnceCommitSession:
    """
    Delegate an AsyncSession while failing exactly one commit.

    Candidate persistence flushes its revision before calling commit.
    Raising here simulates a process/database failure at that boundary.
    """

    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.commit_calls = 0
        self.failed = False

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    async def commit(self) -> None:
        self.commit_calls += 1

        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated crash after candidate revision flush")

        await self.delegate.commit()

    async def rollback(self) -> None:
        await self.delegate.rollback()


async def _persist_resolution_parent(
    db,
    *,
    user_id: UUID,
    base_source,
) -> UUID:
    source_event = await PlatformEventStore(db).append(
        user_id=user_id,
        event_type=("customer_service.support.outcome.evaluated"),
        source="test.slice_7i",
        payload={
            "objective_ref": base_source.objective_ref,
            "evaluation_ref": base_source.evaluation_ref,
        },
        meta={
            "slice": "7i",
            "informational_only": True,
            "failure_testing": True,
        },
        commit=True,
    )

    assessment = ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace=base_source.objective_namespace,
            objective_type=base_source.objective_type,
            objective_ref=base_source.objective_ref,
            objective_version=base_source.objective_version,
        ),
        source=ObjectiveResolutionSource(
            outcome_ref=base_source.outcome_ref,
            outcome_version=1,
            evaluation_ref=base_source.evaluation_ref,
            evaluation_version=1,
            workflow_run_id=base_source.workflow_run_id,
        ),
        status=ObjectiveResolutionStatus.ACHIEVED,
        reason_code="verified_customer_support_outcome",
        summary=(
            "Customer-support objective was verified before retry-recovery testing."
        ),
        confidence=1.0,
        is_terminal=True,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="verified-support-operation",
                operation_type="customer_support_resolution",
                status=ObjectiveOperationStatus.ACHIEVED,
                required=True,
                reason_code="verified_outcome",
                summary=("Required support operation was verified."),
                evidence_refs=tuple(base_source.evidence_refs),
            ),
        ),
        metadata={
            "slice": "7i",
            "informational_only": True,
            "authorizes_execution": False,
        },
    )

    write = await ObjectiveResolutionService(db).record_assessment(
        source_event_id=source_event.id,
        user_id=user_id,
        tenant_id=base_source.tenant_id,
        assessment=assessment,
        projection_version=1,
    )

    assert write.created is True
    assert write.event_id is not None

    return write.record.id


def _source_for_resolution(
    *,
    base_source,
    user_id: UUID,
    resolution_record_id: UUID,
):
    return base_source.model_copy(
        update={
            "user_id": str(user_id),
            "resolution_record_id": str(resolution_record_id),
        }
    )


async def _summarize_one_experience(
    db,
    *,
    user_id: UUID,
    experience_repository,
    record,
    now: datetime,
) -> ObjectiveLearningAggregation:
    service = ObjectiveLearningSummaryService(
        db=db,
        repository=experience_repository,
        aggregation_policy=(
            ObjectiveLearningAggregationPolicy(minimum_effective_sample_size=0.5)
        ),
    )

    summaries = await service.summarize(
        user_id=user_id,
        window_hours=24,
        tenant_id=record.tenant_id,
        objective_namespace=record.objective_namespace,
        objective_type=record.objective_type,
        now=now,
    )

    assert len(summaries) == 1

    return summaries[0]


def _lifecycle(db) -> ObjectiveLearningLifecycleOperations:
    return ObjectiveLearningLifecycleOperations(
        db=db,
        repository=ObjectiveLearningCandidateRepository(db),
        factory=ObjectiveLearningCandidateFactory(
            policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
        ),
    )


@pytest.mark.asyncio
async def test_experience_crash_rolls_back_and_retry_converges():
    """
    A crash after repository flush but before service commit must
    leave no experience. A fresh-session retry must create exactly
    one durable experience, and later retries must resolve it.
    """

    user_id = uuid4()
    base_source = _canonical_source()

    async with SessionLocal() as db:
        resolution_record_id = await _persist_resolution_parent(
            db,
            user_id=user_id,
            base_source=base_source,
        )

    source = _source_for_resolution(
        base_source=base_source,
        user_id=user_id,
        resolution_record_id=resolution_record_id,
    )

    failed_loader = StaticCanonicalSourceLoader(source)

    async with SessionLocal() as failing_db:
        failing_repository = FailAfterExperienceFlushRepository(failing_db)

        service = CustomerSupportObjectiveLearningRecordingService(
            failing_db,
            source_loader=failed_loader,
            repository=failing_repository,
        )

        with pytest.raises(
            RuntimeError,
            match="simulated crash after experience flush",
        ):
            await service.record_for_resolution(
                user_id=user_id,
                resolution_record_id=resolution_record_id,
            )

        assert failing_repository.calls == 1

    async with SessionLocal() as verification_db:
        after_failure_count = await verification_db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == user_id,
                ObjectiveLearningExperienceRecord.resolution_record_id
                == resolution_record_id,
            )
        )

    assert after_failure_count == 0

    retry_loader = StaticCanonicalSourceLoader(source)

    async with SessionLocal() as retry_db:
        service = CustomerSupportObjectiveLearningRecordingService(
            retry_db,
            source_loader=retry_loader,
            repository=(ObjectiveLearningExperienceRepository(retry_db)),
        )

        recovered = await service.record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        repeated = await service.record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        assert recovered.created is True
        assert repeated.created is False
        assert recovered.record.id == repeated.record.id
        assert recovered.experience == repeated.experience

    async with SessionLocal() as final_db:
        final_count = await final_db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == user_id,
                ObjectiveLearningExperienceRecord.resolution_record_id
                == resolution_record_id,
            )
        )

    assert final_count == 1
    assert len(failed_loader.calls) == 1
    assert len(retry_loader.calls) == 2


@pytest.mark.asyncio
async def test_candidate_crashes_retry_to_one_safe_history():
    """
    Proposal and approval failures after flush but before commit
    must roll back completely. Fresh-session retries create only
    revisions 1 and 2. A repeated terminal review is rejected and
    cannot create revision 3.
    """

    user_id = uuid4()
    reviewer_id = uuid4()
    base_source = _canonical_source()

    async with SessionLocal() as setup_db:
        resolution_record_id = await _persist_resolution_parent(
            setup_db,
            user_id=user_id,
            base_source=base_source,
        )

        source = _source_for_resolution(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        recording = await CustomerSupportObjectiveLearningRecordingService(
            setup_db,
            source_loader=(StaticCanonicalSourceLoader(source)),
            repository=(ObjectiveLearningExperienceRepository(setup_db)),
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        aggregation_now = datetime.now(timezone.utc) + timedelta(seconds=1)

        aggregation = await _summarize_one_experience(
            setup_db,
            user_id=user_id,
            experience_repository=(ObjectiveLearningExperienceRepository(setup_db)),
            record=recording.record,
            now=aggregation_now,
        )

    # Simulate proposal revision 1 flushing and commit failing.
    async with SessionLocal() as proposal_db:
        failing_session = FailOnceCommitSession(proposal_db)
        lifecycle = _lifecycle(failing_session)

        with pytest.raises(
            RuntimeError,
            match=("simulated crash after candidate revision flush"),
        ):
            await lifecycle.propose(
                user_id=user_id,
                aggregation=aggregation,
                proposed_at=aggregation_now,
            )

        assert failing_session.commit_calls == 1
        await failing_session.rollback()

    async with SessionLocal() as verify_proposal_db:
        after_proposal_failure = await verify_proposal_db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(ObjectiveLearningCandidateRevisionRecord.user_id == user_id)
        )

    assert after_proposal_failure == 0

    # A fresh worker/session retries proposal successfully.
    async with SessionLocal() as proposal_retry_db:
        lifecycle = _lifecycle(proposal_retry_db)

        proposal = await lifecycle.propose(
            user_id=user_id,
            aggregation=aggregation,
            proposed_at=aggregation_now,
        )

        repeated_proposal = await lifecycle.propose(
            user_id=user_id,
            aggregation=aggregation,
            proposed_at=aggregation_now,
        )

        assert proposal.created is True
        assert repeated_proposal.created is False
        assert proposal.candidate == repeated_proposal.candidate
        assert proposal.candidate.candidate_version == 1

        candidate_id = proposal.candidate.candidate_id

    review_request = ObjectiveLearningCandidateReviewRequest(
        decision=ObjectiveLearningReviewDecision.APPROVE,
        reason=("Verified evidence accepted after recovery."),
        reviewed_at=(aggregation_now + timedelta(seconds=1)),
    )

    # Simulate revision 2 flushing and commit failing.
    async with SessionLocal() as review_db:
        failing_session = FailOnceCommitSession(review_db)
        lifecycle = _lifecycle(failing_session)

        with pytest.raises(
            RuntimeError,
            match=("simulated crash after candidate revision flush"),
        ):
            await lifecycle.review(
                user_id=user_id,
                candidate_id=candidate_id,
                reviewed_by_user_id=reviewer_id,
                request=review_request,
            )

        assert failing_session.commit_calls == 1
        await failing_session.rollback()

    async with SessionLocal() as verify_review_db:
        versions_after_review_failure = list(
            (
                await verify_review_db.execute(
                    select(ObjectiveLearningCandidateRevisionRecord.version)
                    .where(
                        ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                        ObjectiveLearningCandidateRevisionRecord.candidate_id
                        == candidate_id,
                    )
                    .order_by(ObjectiveLearningCandidateRevisionRecord.version)
                )
            )
            .scalars()
            .all()
        )

    assert versions_after_review_failure == [1]

    # A fresh worker/session retries approval successfully.
    async with SessionLocal() as review_retry_db:
        lifecycle = _lifecycle(review_retry_db)

        approved = await lifecycle.review(
            user_id=user_id,
            candidate_id=candidate_id,
            reviewed_by_user_id=reviewer_id,
            request=review_request,
        )

        assert approved is not None
        assert approved.candidate_version == 2
        assert approved.status.value == "approved"
        assert approved.approval_status.value == "approved"
        assert approved.informational_only is True
        assert approved.authorizes_execution is False

        # Once durable approval exists, the same review request is
        # terminally invalid rather than creating another revision.
        with pytest.raises(
            ValueError,
            match=(
                "Only a pending validated objective learning candidate can be reviewed"
            ),
        ):
            await lifecycle.review(
                user_id=user_id,
                candidate_id=candidate_id,
                reviewed_by_user_id=reviewer_id,
                request=review_request,
            )

        history = await lifecycle.history(
            user_id=user_id,
            candidate_id=candidate_id,
        )

        assert [item.candidate_version for item in history] == [1, 2]
        assert history[0].status.value == "validated"
        assert history[1].status.value == "approved"

    async with SessionLocal() as final_db:
        final_versions = list(
            (
                await final_db.execute(
                    select(ObjectiveLearningCandidateRevisionRecord.version)
                    .where(
                        ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                        ObjectiveLearningCandidateRevisionRecord.candidate_id
                        == candidate_id,
                    )
                    .order_by(ObjectiveLearningCandidateRevisionRecord.version)
                )
            )
            .scalars()
            .all()
        )

    assert final_versions == [1, 2]
