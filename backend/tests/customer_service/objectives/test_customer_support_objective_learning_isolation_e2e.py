from __future__ import annotations

from dataclasses import dataclass
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
    CustomerSupportObjectiveLearningRecordingResult,
    CustomerSupportObjectiveLearningRecordingService,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningAggregation,
    ObjectiveLearningAggregationPolicy,
    ObjectiveLearningApprovedInsight,
    ObjectiveLearningApprovedInsightService,
    ObjectiveLearningCandidate,
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


TENANT_A = "tenant-isolation-a"
TENANT_B = "tenant-isolation-b"


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


@dataclass(frozen=True)
class CompletedLearningLifecycle:
    user_id: UUID
    tenant_id: str
    resolution_record_id: UUID
    recording: CustomerSupportObjectiveLearningRecordingResult
    aggregation: ObjectiveLearningAggregation
    proposed: ObjectiveLearningCandidate
    approved: ObjectiveLearningCandidate
    insight: ObjectiveLearningApprovedInsight


async def _persist_resolution(
    db,
    *,
    user_id: UUID,
    tenant_id: str,
    base_source,
) -> UUID:
    source_event = await PlatformEventStore(db).append(
        user_id=user_id,
        event_type=("customer_service.support.outcome.evaluated"),
        source="test.slice_7j",
        payload={
            "objective_ref": base_source.objective_ref,
            "evaluation_ref": base_source.evaluation_ref,
            "tenant_id": tenant_id,
        },
        meta={
            "slice": "7j",
            "tenant_id": tenant_id,
            "informational_only": True,
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
            "Customer-support objective was verified "
            "for authenticated isolation testing."
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
            "slice": "7j",
            "tenant_id": tenant_id,
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


def _source_for_owner(
    *,
    base_source,
    user_id: UUID,
    tenant_id: str,
    resolution_record_id: UUID,
):
    # The canonical source owns tenant_id directly. The extractor
    # derives validity_scope later from canonical source facts.
    return base_source.model_copy(
        update={
            "user_id": str(user_id),
            "tenant_id": tenant_id,
            "resolution_record_id": str(resolution_record_id),
        }
    )


def _lifecycle(db) -> ObjectiveLearningLifecycleOperations:
    return ObjectiveLearningLifecycleOperations(
        db=db,
        repository=ObjectiveLearningCandidateRepository(db),
        factory=ObjectiveLearningCandidateFactory(
            policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
        ),
    )


async def _complete_lifecycle(
    db,
    *,
    user_id: UUID,
    tenant_id: str,
    reviewer_id: UUID,
    base_source,
    now: datetime,
) -> CompletedLearningLifecycle:
    resolution_record_id = await _persist_resolution(
        db,
        user_id=user_id,
        tenant_id=tenant_id,
        base_source=base_source,
    )

    source = _source_for_owner(
        base_source=base_source,
        user_id=user_id,
        tenant_id=tenant_id,
        resolution_record_id=resolution_record_id,
    )

    loader = StaticCanonicalSourceLoader(source)
    experience_repository = ObjectiveLearningExperienceRepository(db)

    recording = await CustomerSupportObjectiveLearningRecordingService(
        db,
        source_loader=loader,
        repository=experience_repository,
    ).record_for_resolution(
        user_id=user_id,
        resolution_record_id=resolution_record_id,
        tenant_id=tenant_id,
    )

    assert recording.created is True
    assert recording.record.user_id == user_id
    assert recording.record.tenant_id == tenant_id
    assert recording.experience.user_id == str(user_id)
    assert recording.experience.validity_scope.tenant_id == tenant_id

    summary_service = ObjectiveLearningSummaryService(
        db=db,
        repository=experience_repository,
        aggregation_policy=(
            ObjectiveLearningAggregationPolicy(minimum_effective_sample_size=0.5)
        ),
    )

    summaries = await summary_service.summarize(
        user_id=user_id,
        window_hours=24,
        tenant_id=tenant_id,
        objective_namespace=(recording.record.objective_namespace),
        objective_type=(recording.record.objective_type),
        now=now,
    )

    assert len(summaries) == 1

    aggregation = summaries[0]

    assert aggregation.tenant_id == tenant_id
    assert aggregation.total_experiences == 1
    assert aggregation.informational_only is True
    assert aggregation.authorizes_execution is False

    lifecycle = _lifecycle(db)

    proposal = await lifecycle.propose(
        user_id=user_id,
        aggregation=aggregation,
        proposed_at=now,
    )

    assert proposal.created is True
    assert proposal.candidate.candidate_version == 1
    assert proposal.candidate.status.value == "validated"
    assert proposal.candidate.approval_status.value == "pending"

    approved = await lifecycle.review(
        user_id=user_id,
        candidate_id=(proposal.candidate.candidate_id),
        reviewed_by_user_id=reviewer_id,
        request=ObjectiveLearningCandidateReviewRequest(
            decision=ObjectiveLearningReviewDecision.APPROVE,
            reason=(f"Authenticated owner accepted evidence for {tenant_id}."),
            reviewed_at=now + timedelta(seconds=1),
        ),
    )

    assert approved is not None
    assert approved.candidate_version == 2
    assert approved.status.value == "approved"
    assert approved.approval_status.value == "approved"
    assert approved.informational_only is True
    assert approved.authorizes_execution is False

    insight = await ObjectiveLearningApprovedInsightService(
        db=db,
        repository=ObjectiveLearningCandidateRepository(db),
    ).get_approved(
        user_id=user_id,
        candidate_id=approved.candidate_id,
    )

    assert insight is not None
    assert insight.tenant_id == tenant_id
    assert insight.informational_only is True
    assert insight.authorizes_execution is False

    assert loader.calls == [
        {
            "user_id": user_id,
            "resolution_record_id": (resolution_record_id),
            "tenant_id": tenant_id,
        }
    ]

    return CompletedLearningLifecycle(
        user_id=user_id,
        tenant_id=tenant_id,
        resolution_record_id=resolution_record_id,
        recording=recording,
        aggregation=aggregation,
        proposed=proposal.candidate,
        approved=approved,
        insight=insight,
    )


@pytest.mark.asyncio
async def test_user_and_tenant_learning_lifecycles_are_isolated():
    """
    Two users use identical semantic learning contracts while
    belonging to different tenants. Every durable and advisory
    boundary must remain isolated by authenticated ownership and
    tenant scope.
    """

    user_a = uuid4()
    user_b = uuid4()
    reviewer_a = uuid4()
    reviewer_b = uuid4()

    base_source = _canonical_source()

    now = datetime.now(timezone.utc) + timedelta(seconds=1)

    async with SessionLocal() as db:
        lifecycle_a = await _complete_lifecycle(
            db,
            user_id=user_a,
            tenant_id=TENANT_A,
            reviewer_id=reviewer_a,
            base_source=base_source,
            now=now,
        )

        lifecycle_b = await _complete_lifecycle(
            db,
            user_id=user_b,
            tenant_id=TENANT_B,
            reviewer_id=reviewer_b,
            base_source=base_source,
            now=now,
        )

        # Both owners used the same semantic contracts. Only user
        # ownership and tenant validity scope differ.
        assert (
            lifecycle_a.recording.record.objective_namespace
            == lifecycle_b.recording.record.objective_namespace
        )
        assert (
            lifecycle_a.recording.record.objective_type
            == lifecycle_b.recording.record.objective_type
        )
        assert (
            lifecycle_a.recording.record.objective_ref
            == lifecycle_b.recording.record.objective_ref
        )
        assert (
            lifecycle_a.recording.record.schema_ref
            == lifecycle_b.recording.record.schema_ref
        )
        assert (
            lifecycle_a.recording.record.profile_ref
            == lifecycle_b.recording.record.profile_ref
        )
        assert (
            lifecycle_a.recording.record.extractor_ref
            == lifecycle_b.recording.record.extractor_ref
        )

        assert lifecycle_a.user_id != lifecycle_b.user_id
        assert lifecycle_a.tenant_id != lifecycle_b.tenant_id
        assert lifecycle_a.resolution_record_id != lifecycle_b.resolution_record_id
        assert lifecycle_a.recording.record.id != lifecycle_b.recording.record.id

        experience_repository = ObjectiveLearningExperienceRepository(db)

        # Exact experience reads never cross authenticated users.
        assert (
            await experience_repository.get_for_user(
                user_id=user_b,
                record_id=(lifecycle_a.recording.record.id),
            )
            is None
        )

        assert (
            await experience_repository.get_for_user(
                user_id=user_a,
                record_id=(lifecycle_b.recording.record.id),
            )
            is None
        )

        assert (
            await experience_repository.list_for_resolution(
                user_id=user_b,
                resolution_record_id=(lifecycle_a.resolution_record_id),
            )
            == []
        )

        assert (
            await experience_repository.list_for_resolution(
                user_id=user_a,
                resolution_record_id=(lifecycle_b.resolution_record_id),
            )
            == []
        )

        summary_service = ObjectiveLearningSummaryService(
            db=db,
            repository=experience_repository,
            aggregation_policy=(
                ObjectiveLearningAggregationPolicy(minimum_effective_sample_size=0.5)
            ),
        )

        common_summary_scope = {
            "window_hours": 24,
            "objective_namespace": (lifecycle_a.recording.record.objective_namespace),
            "objective_type": (lifecycle_a.recording.record.objective_type),
            "now": now,
        }

        # The correct owner and tenant see one aggregation.
        summaries_a = await summary_service.summarize(
            user_id=user_a,
            tenant_id=TENANT_A,
            **common_summary_scope,
        )
        summaries_b = await summary_service.summarize(
            user_id=user_b,
            tenant_id=TENANT_B,
            **common_summary_scope,
        )

        assert len(summaries_a) == 1
        assert len(summaries_b) == 1
        assert summaries_a[0].tenant_id == TENANT_A
        assert summaries_b[0].tenant_id == TENANT_B
        assert summaries_a[0].total_experiences == 1
        assert summaries_b[0].total_experiences == 1

        # Correct user with the other tenant sees nothing.
        assert (
            await summary_service.summarize(
                user_id=user_a,
                tenant_id=TENANT_B,
                **common_summary_scope,
            )
            == []
        )

        assert (
            await summary_service.summarize(
                user_id=user_b,
                tenant_id=TENANT_A,
                **common_summary_scope,
            )
            == []
        )

        # Even without a tenant filter, authenticated ownership
        # prevents either user's evidence from entering the other
        # user's aggregation.
        all_user_a = await summary_service.summarize(
            user_id=user_a,
            tenant_id=None,
            **common_summary_scope,
        )
        all_user_b = await summary_service.summarize(
            user_id=user_b,
            tenant_id=None,
            **common_summary_scope,
        )

        assert len(all_user_a) == 1
        assert len(all_user_b) == 1
        assert all_user_a[0].tenant_id == TENANT_A
        assert all_user_b[0].tenant_id == TENANT_B
        assert all_user_a[0].total_experiences == 1
        assert all_user_b[0].total_experiences == 1

        lifecycle_operations = _lifecycle(db)

        # Candidate reads are authenticated.
        assert (
            await lifecycle_operations.get_latest(
                user_id=user_b,
                candidate_id=(lifecycle_a.approved.candidate_id),
            )
            is None
        )

        assert (
            await lifecycle_operations.get_latest(
                user_id=user_a,
                candidate_id=(lifecycle_b.approved.candidate_id),
            )
            is None
        )

        assert (
            await lifecycle_operations.history(
                user_id=user_b,
                candidate_id=(lifecycle_a.approved.candidate_id),
            )
            == []
        )

        assert (
            await lifecycle_operations.history(
                user_id=user_a,
                candidate_id=(lifecycle_b.approved.candidate_id),
            )
            == []
        )

        # Cross-user review behaves as not found and appends no
        # revision to either owner's immutable history.
        cross_review_a = await lifecycle_operations.review(
            user_id=user_b,
            candidate_id=(lifecycle_a.approved.candidate_id),
            reviewed_by_user_id=reviewer_b,
            request=ObjectiveLearningCandidateReviewRequest(
                decision=(ObjectiveLearningReviewDecision.REJECT),
                reason=("Cross-user review must not be applied."),
                reviewed_at=now + timedelta(seconds=2),
            ),
        )

        cross_review_b = await lifecycle_operations.review(
            user_id=user_a,
            candidate_id=(lifecycle_b.approved.candidate_id),
            reviewed_by_user_id=reviewer_a,
            request=ObjectiveLearningCandidateReviewRequest(
                decision=(ObjectiveLearningReviewDecision.REJECT),
                reason=("Cross-user review must not be applied."),
                reviewed_at=now + timedelta(seconds=2),
            ),
        )

        assert cross_review_a is None
        assert cross_review_b is None

        history_a = await lifecycle_operations.history(
            user_id=user_a,
            candidate_id=(lifecycle_a.approved.candidate_id),
        )
        history_b = await lifecycle_operations.history(
            user_id=user_b,
            candidate_id=(lifecycle_b.approved.candidate_id),
        )

        assert [item.candidate_version for item in history_a] == [1, 2]
        assert [item.candidate_version for item in history_b] == [1, 2]

        approved_service = ObjectiveLearningApprovedInsightService(
            db=db,
            repository=(ObjectiveLearningCandidateRepository(db)),
        )

        # Direct approved retrieval never crosses users.
        assert (
            await approved_service.get_approved(
                user_id=user_b,
                candidate_id=(lifecycle_a.approved.candidate_id),
            )
            is None
        )

        assert (
            await approved_service.get_approved(
                user_id=user_a,
                candidate_id=(lifecycle_b.approved.candidate_id),
            )
            is None
        )

        common_list_scope = {
            "objective_namespace": (lifecycle_a.aggregation.objective_namespace),
            "objective_type": (lifecycle_a.aggregation.objective_type),
        }

        approved_a = await approved_service.list_approved(
            user_id=user_a,
            tenant_id=TENANT_A,
            **common_list_scope,
        )
        approved_b = await approved_service.list_approved(
            user_id=user_b,
            tenant_id=TENANT_B,
            **common_list_scope,
        )

        assert [item.provenance.candidate_id for item in approved_a] == [
            lifecycle_a.approved.candidate_id
        ]

        assert [item.provenance.candidate_id for item in approved_b] == [
            lifecycle_b.approved.candidate_id
        ]

        # Correct owner with the wrong tenant sees no approved
        # advisory projection.
        assert (
            await approved_service.list_approved(
                user_id=user_a,
                tenant_id=TENANT_B,
                **common_list_scope,
            )
            == []
        )

        assert (
            await approved_service.list_approved(
                user_id=user_b,
                tenant_id=TENANT_A,
                **common_list_scope,
            )
            == []
        )

        experience_counts = dict(
            (
                await db.execute(
                    select(
                        ObjectiveLearningExperienceRecord.user_id,
                        func.count(),
                    )
                    .where(
                        ObjectiveLearningExperienceRecord.user_id.in_([user_a, user_b])
                    )
                    .group_by(ObjectiveLearningExperienceRecord.user_id)
                )
            ).all()
        )

        revision_counts = dict(
            (
                await db.execute(
                    select(
                        ObjectiveLearningCandidateRevisionRecord.user_id,
                        func.count(),
                    )
                    .where(
                        ObjectiveLearningCandidateRevisionRecord.user_id.in_(
                            [user_a, user_b]
                        )
                    )
                    .group_by(ObjectiveLearningCandidateRevisionRecord.user_id)
                )
            ).all()
        )

        assert experience_counts == {
            user_a: 1,
            user_b: 1,
        }

        assert revision_counts == {
            user_a: 2,
            user_b: 2,
        }

        assert lifecycle_a.insight.informational_only is True
        assert lifecycle_b.insight.informational_only is True
        assert lifecycle_a.insight.affects_ranking is False
        assert lifecycle_b.insight.affects_ranking is False
        assert lifecycle_a.insight.affects_capability_selection is False
        assert lifecycle_b.insight.affects_capability_selection is False
        assert lifecycle_a.insight.selects_provider is False
        assert lifecycle_b.insight.selects_provider is False
        assert lifecycle_a.insight.authorizes_execution is False
        assert lifecycle_b.insight.authorizes_execution is False
