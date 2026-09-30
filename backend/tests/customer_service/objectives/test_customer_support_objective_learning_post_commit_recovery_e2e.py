from __future__ import annotations

from datetime import datetime, timedelta, timezone
import runpy
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningApprovedInsightService,
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateRepository,
    ObjectiveLearningCandidateReviewRequest,
    ObjectiveLearningLifecycleOperations,
    ObjectiveLearningReviewDecision,
)


POST_COMMIT_ERROR = "simulated process crash after durable candidate commit"


def _slice_7i_helpers() -> dict[str, Any]:
    """
    Reuse Slice 7I's proven durable experience and aggregation setup.

    Slice 7O changes only the location of the injected failure:
    after repository commit instead of before commit.
    """

    return runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_retry_recovery_e2e.py"
    )


class FailAfterDurableAppendRepository:
    """
    Delegate a candidate append completely, including its internal
    commit and refresh, then lose the successful response once.

    This models a process or network failure after PostgreSQL has
    committed but before the caller receives confirmation.
    """

    def __init__(
        self,
        db,
        *,
        fail_on_version: int,
    ) -> None:
        self.delegate = ObjectiveLearningCandidateRepository(db)
        self.fail_on_version = fail_on_version
        self.append_calls = 0
        self.failed = False

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    async def append_revision(
        self,
        *,
        user_id,
        candidate,
    ):
        self.append_calls += 1

        row = await self.delegate.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        if not self.failed and candidate.candidate_version == self.fail_on_version:
            self.failed = True
            raise RuntimeError(POST_COMMIT_ERROR)

        return row


def _lifecycle(
    db,
    *,
    repository=None,
) -> ObjectiveLearningLifecycleOperations:
    return ObjectiveLearningLifecycleOperations(
        db=db,
        repository=(repository or ObjectiveLearningCandidateRepository(db)),
        factory=ObjectiveLearningCandidateFactory(
            policy=ObjectiveLearningCandidatePolicy(
                minimum_summary_confidence=0.0,
            )
        ),
    )


@pytest.mark.asyncio
async def test_post_commit_response_loss_converges_from_durable_state():
    """
    A process may fail after PostgreSQL commits but before the caller
    receives the successful result.

    Proposal retry must discover the already committed candidate.
    Approval retry must observe the already committed terminal state,
    refuse a duplicate review, and expose the committed approved
    insight through authenticated reads.
    """

    helpers = _slice_7i_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_resolution = helpers["_source_for_resolution"]
    summarize_one_experience = helpers["_summarize_one_experience"]
    static_source_loader = helpers["StaticCanonicalSourceLoader"]

    recording_service_type = helpers["CustomerSupportObjectiveLearningRecordingService"]
    experience_repository_type = helpers["ObjectiveLearningExperienceRepository"]

    user_id = uuid4()
    reviewer_id = uuid4()
    base_source = canonical_source()

    async with SessionLocal() as setup_db:
        resolution_record_id = await persist_resolution_parent(
            setup_db,
            user_id=user_id,
            base_source=base_source,
        )

        source = source_for_resolution(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        experience_repository = experience_repository_type(setup_db)

        recording = await recording_service_type(
            setup_db,
            source_loader=static_source_loader(source),
            repository=experience_repository,
        ).record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        aggregation_now = datetime.now(timezone.utc) + timedelta(seconds=1)

        aggregation = await summarize_one_experience(
            setup_db,
            user_id=user_id,
            experience_repository=experience_repository,
            record=recording.record,
            now=aggregation_now,
        )

    # ---------------------------------------------------------
    # Proposal version 1 commits, but its success response is lost.
    # ---------------------------------------------------------
    async with SessionLocal() as proposal_failure_db:
        failing_repository = FailAfterDurableAppendRepository(
            proposal_failure_db,
            fail_on_version=1,
        )
        lifecycle = _lifecycle(
            proposal_failure_db,
            repository=failing_repository,
        )

        with pytest.raises(
            RuntimeError,
            match=POST_COMMIT_ERROR,
        ):
            await lifecycle.propose(
                user_id=user_id,
                aggregation=aggregation,
                proposed_at=aggregation_now,
            )

        assert failing_repository.append_calls == 1
        assert failing_repository.failed is True

    # A separate session must see the committed version 1 even
    # though the original caller received an exception.
    async with SessionLocal() as verify_proposal_db:
        proposal_rows = list(
            (
                await verify_proposal_db.execute(
                    select(ObjectiveLearningCandidateRevisionRecord).where(
                        ObjectiveLearningCandidateRevisionRecord.user_id == user_id
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(proposal_rows) == 1
        assert proposal_rows[0].version == 1
        assert proposal_rows[0].status == "validated"
        assert proposal_rows[0].approval_status == "pending"

        candidate_id = proposal_rows[0].candidate_id

    # Retrying proposal must resolve the committed candidate and
    # must not attempt another append.
    async with SessionLocal() as proposal_retry_db:
        lifecycle = _lifecycle(proposal_retry_db)

        recovered_proposal = await lifecycle.propose(
            user_id=user_id,
            aggregation=aggregation,
            proposed_at=(aggregation_now + timedelta(seconds=1)),
        )

        assert recovered_proposal.created is False
        assert recovered_proposal.candidate.candidate_id == candidate_id
        assert recovered_proposal.candidate.candidate_version == 1
        assert recovered_proposal.candidate.status.value == "validated"
        assert recovered_proposal.candidate.approval_status.value == "pending"

    review_request = ObjectiveLearningCandidateReviewRequest(
        decision=(ObjectiveLearningReviewDecision.APPROVE),
        reason=("Verified evidence accepted despite post-commit response loss."),
        reviewed_at=(aggregation_now + timedelta(seconds=2)),
    )

    # ---------------------------------------------------------
    # Approval version 2 commits, but its success response is lost.
    # ---------------------------------------------------------
    async with SessionLocal() as review_failure_db:
        failing_repository = FailAfterDurableAppendRepository(
            review_failure_db,
            fail_on_version=2,
        )
        lifecycle = _lifecycle(
            review_failure_db,
            repository=failing_repository,
        )

        with pytest.raises(
            RuntimeError,
            match=POST_COMMIT_ERROR,
        ):
            await lifecycle.review(
                user_id=user_id,
                candidate_id=candidate_id,
                reviewed_by_user_id=reviewer_id,
                request=review_request,
            )

        assert failing_repository.append_calls == 1
        assert failing_repository.failed is True

    # The committed state must contain contiguous immutable
    # versions [1, 2], never a partial or duplicate revision.
    async with SessionLocal() as verify_review_db:
        versions = list(
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

        latest_row = await verify_review_db.scalar(
            select(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id == candidate_id,
            )
            .order_by(ObjectiveLearningCandidateRevisionRecord.version.desc())
            .limit(1)
        )

        assert versions == [1, 2]
        assert latest_row is not None
        assert latest_row.version == 2
        assert latest_row.status == "approved"
        assert latest_row.approval_status == "approved"
        assert latest_row.validation_passed is True
        assert latest_row.reviewed_by_user_id == reviewer_id
        assert latest_row.informational_only is True
        assert latest_row.authorizes_execution is False

    # Retrying the same review must not append version 3. The
    # committed version 2 is already terminal.
    async with SessionLocal() as review_retry_db:
        lifecycle = _lifecycle(review_retry_db)

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

        assert [candidate.candidate_version for candidate in history] == [1, 2]
        assert history[0].status.value == "validated"
        assert history[1].status.value == "approved"

        approved_service = ObjectiveLearningApprovedInsightService(
            db=review_retry_db,
            repository=(ObjectiveLearningCandidateRepository(review_retry_db)),
        )

        insight = await approved_service.get_approved(
            user_id=user_id,
            candidate_id=candidate_id,
        )
        approved_list = await approved_service.list_approved(
            user_id=user_id,
            tenant_id=aggregation.tenant_id,
            objective_namespace=(aggregation.objective_namespace),
            objective_type=(aggregation.objective_type),
        )

        assert insight is not None
        assert approved_list == [insight]
        assert insight.provenance.candidate_id == candidate_id
        assert insight.provenance.candidate_version == 2
        assert insight.provenance.reviewed_by_user_id == reviewer_id
        assert insight.informational_only is True
        assert insight.affects_ranking is False
        assert insight.affects_capability_selection is False
        assert insight.affects_business_plan is False
        assert insight.selects_provider is False
        assert insight.authorizes_execution is False
        assert insight.bypasses_approval is False
        assert insight.bypasses_verification is False

    async with SessionLocal() as final_db:
        final_revision_count = await final_db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id == candidate_id,
            )
        )

        assert final_revision_count == 2
