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
from app.runtime.objectives.learning.aggregation import (
    objective_learning_aggregation_key,
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


TENANT_ID = "tenant-scope-separation"
WORKFLOW_TEMPLATE_REF = "customer-support-resolution"
WORKFLOW_VERSION_A = "1"
WORKFLOW_VERSION_B = "2"


def _slice_7k_helpers() -> dict[str, Any]:
    return runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_mixed_evidence_e2e.py"
    )


class SourceMapLoader:
    def __init__(
        self,
        sources: dict[UUID, Any],
    ) -> None:
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


def _lifecycle(
    db,
) -> ObjectiveLearningLifecycleOperations:
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
async def test_workflow_versions_remain_separate_learning_scopes():
    """
    Two experiences belong to the same user, tenant, objective
    family, profile, extractor, and workflow template.

    Their reusable workflow versions differ. They must therefore
    produce separate aggregations, fingerprints, candidates, and
    approved-read results. Approval in one scope must not generalize
    into the other scope.
    """

    helpers = _slice_7k_helpers()

    canonical_source = helpers["_canonical_source"]
    persist_resolution_parent = helpers["_persist_resolution_parent"]
    source_for_case = helpers["_source_for_case"]

    user_id = uuid4()
    reviewer_id = uuid4()
    base_source = canonical_source()

    async with SessionLocal() as db:
        resolution_a = await persist_resolution_parent(
            db,
            user_id=user_id,
            tenant_id=TENANT_ID,
            base_source=base_source,
            case_ref="scope-version-1",
            operation_status="achieved",
        )
        resolution_b = await persist_resolution_parent(
            db,
            user_id=user_id,
            tenant_id=TENANT_ID,
            base_source=base_source,
            case_ref="scope-version-2",
            operation_status="achieved",
        )

        source_a = source_for_case(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=resolution_a,
            case_ref="scope-version-1",
            operation_status="achieved",
            confidence=1.0,
        ).model_copy(
            update={
                "tenant_id": TENANT_ID,
                "workflow_template_ref": (WORKFLOW_TEMPLATE_REF),
                "workflow_version": WORKFLOW_VERSION_A,
                "workflow_run_id": ("scope-version-1-run"),
            }
        )

        source_b = source_for_case(
            base_source=base_source,
            user_id=user_id,
            resolution_record_id=resolution_b,
            case_ref="scope-version-2",
            operation_status="achieved",
            confidence=1.0,
        ).model_copy(
            update={
                "tenant_id": TENANT_ID,
                "workflow_template_ref": (WORKFLOW_TEMPLATE_REF),
                "workflow_version": WORKFLOW_VERSION_B,
                "workflow_run_id": ("scope-version-2-run"),
            }
        )

        loader = SourceMapLoader(
            {
                resolution_a: source_a,
                resolution_b: source_b,
            }
        )
        experience_repository = ObjectiveLearningExperienceRepository(db)
        recording_service = CustomerSupportObjectiveLearningRecordingService(
            db,
            source_loader=loader,
            repository=experience_repository,
        )

        recorded_a = await recording_service.record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_a,
            tenant_id=TENANT_ID,
        )
        recorded_b = await recording_service.record_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_b,
            tenant_id=TENANT_ID,
        )

        assert recorded_a.created is True
        assert recorded_b.created is True

        assert (
            recorded_a.experience.validity_scope.workflow_template_ref
            == WORKFLOW_TEMPLATE_REF
        )
        assert (
            recorded_b.experience.validity_scope.workflow_template_ref
            == WORKFLOW_TEMPLATE_REF
        )
        assert (
            recorded_a.experience.validity_scope.workflow_version == WORKFLOW_VERSION_A
        )
        assert (
            recorded_b.experience.validity_scope.workflow_version == WORKFLOW_VERSION_B
        )

        # Run IDs are instance lineage. They remain in metadata but
        # are not themselves reusable aggregation boundaries.
        assert (
            recorded_a.experience.validity_scope.metadata["workflow_run_id"]
            == "scope-version-1-run"
        )
        assert (
            recorded_b.experience.validity_scope.metadata["workflow_run_id"]
            == "scope-version-2-run"
        )

        aggregation_key_a = objective_learning_aggregation_key(recorded_a.experience)
        aggregation_key_b = objective_learning_aggregation_key(recorded_b.experience)

        assert aggregation_key_a != aggregation_key_b

        experience_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == user_id,
                ObjectiveLearningExperienceRecord.tenant_id == TENANT_ID,
            )
        )

        assert experience_count == 2
        assert len(loader.calls) == 2

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

        assert len(summaries) == 2

        summaries_by_version = {
            summary.validity_scope["workflow_version"]: summary for summary in summaries
        }

        assert set(summaries_by_version) == {
            WORKFLOW_VERSION_A,
            WORKFLOW_VERSION_B,
        }

        summary_a = summaries_by_version[WORKFLOW_VERSION_A]
        summary_b = summaries_by_version[WORKFLOW_VERSION_B]

        for summary in (
            summary_a,
            summary_b,
        ):
            assert summary.total_experiences == 1
            assert summary.unique_objective_count == 1
            assert summary.unique_resolution_count == 1
            assert summary.unique_outcome_count == 1
            assert summary.unique_evaluation_count == 1
            assert summary.unique_workflow_run_count == 1
            assert summary.evidence_sufficient is True
            assert summary.informational_only is True
            assert summary.authorizes_execution is False
            assert (
                summary.validity_scope["workflow_template_ref"] == WORKFLOW_TEMPLATE_REF
            )

        assert summary_a.scope_fingerprint != summary_b.scope_fingerprint
        assert summary_a.validity_scope["workflow_version"] == WORKFLOW_VERSION_A
        assert summary_b.validity_scope["workflow_version"] == WORKFLOW_VERSION_B

        lifecycle = _lifecycle(db)

        proposal_a = await lifecycle.propose(
            user_id=user_id,
            aggregation=summary_a,
            proposed_at=now,
        )
        proposal_b = await lifecycle.propose(
            user_id=user_id,
            aggregation=summary_b,
            proposed_at=now,
        )

        candidate_a = proposal_a.candidate
        candidate_b = proposal_b.candidate

        assert proposal_a.created is True
        assert proposal_b.created is True

        assert candidate_a.candidate_id != candidate_b.candidate_id
        assert candidate_a.evidence.scope_fingerprint == summary_a.scope_fingerprint
        assert candidate_b.evidence.scope_fingerprint == summary_b.scope_fingerprint

        for candidate in (
            candidate_a,
            candidate_b,
        ):
            assert candidate.candidate_version == 1
            assert candidate.status.value == "validated"
            assert candidate.approval_status.value == "pending"
            assert candidate.validation_passed is True
            assert candidate.informational_only is True
            assert candidate.affects_ranking is False
            assert candidate.affects_capability_selection is False
            assert candidate.affects_business_plan is False
            assert candidate.selects_provider is False
            assert candidate.authorizes_execution is False

        approved_a = await lifecycle.review(
            user_id=user_id,
            candidate_id=candidate_a.candidate_id,
            reviewed_by_user_id=reviewer_id,
            request=(
                ObjectiveLearningCandidateReviewRequest(
                    decision=(ObjectiveLearningReviewDecision.APPROVE),
                    reason=("Accept evidence only for workflow version 1."),
                    reviewed_at=(now + timedelta(seconds=1)),
                )
            ),
        )

        assert approved_a is not None
        assert approved_a.candidate_version == 2
        assert approved_a.status.value == "approved"
        assert approved_a.approval_status.value == "approved"

        # The second exact scope remains unchanged and pending.
        latest_b = await lifecycle.get_latest(
            user_id=user_id,
            candidate_id=candidate_b.candidate_id,
        )
        history_b = await lifecycle.history(
            user_id=user_id,
            candidate_id=candidate_b.candidate_id,
        )

        assert latest_b == candidate_b
        assert history_b == [candidate_b]

        approved_service = ObjectiveLearningApprovedInsightService(
            db=db,
            repository=(ObjectiveLearningCandidateRepository(db)),
        )

        insight_a = await approved_service.get_approved(
            user_id=user_id,
            candidate_id=candidate_a.candidate_id,
        )
        insight_b = await approved_service.get_approved(
            user_id=user_id,
            candidate_id=candidate_b.candidate_id,
        )
        approved_list = await approved_service.list_approved(
            user_id=user_id,
            tenant_id=TENANT_ID,
            objective_namespace=(base_source.objective_namespace),
            objective_type=(base_source.objective_type),
        )

        assert insight_a is not None
        assert insight_b is None
        assert approved_list == [insight_a]

        assert (
            insight_a.validity_scope["workflow_template_ref"] == WORKFLOW_TEMPLATE_REF
        )
        assert insight_a.validity_scope["workflow_version"] == WORKFLOW_VERSION_A
        assert insight_a.provenance.scope_fingerprint == summary_a.scope_fingerprint
        assert insight_a.provenance.scope_fingerprint != summary_b.scope_fingerprint

        assert insight_a.informational_only is True
        assert insight_a.affects_ranking is False
        assert insight_a.affects_capability_selection is False
        assert insight_a.affects_business_plan is False
        assert insight_a.selects_provider is False
        assert insight_a.authorizes_execution is False
        assert insight_a.bypasses_approval is False
        assert insight_a.bypasses_verification is False

        revision_counts = dict(
            (
                await db.execute(
                    select(
                        ObjectiveLearningCandidateRevisionRecord.candidate_id,
                        func.count().label("revision_count"),
                    )
                    .where(
                        ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                        ObjectiveLearningCandidateRevisionRecord.candidate_id.in_(
                            (
                                candidate_a.candidate_id,
                                candidate_b.candidate_id,
                            )
                        ),
                    )
                    .group_by(ObjectiveLearningCandidateRevisionRecord.candidate_id)
                )
            ).all()
        )

        assert revision_counts == {
            candidate_a.candidate_id: 2,
            candidate_b.candidate_id: 1,
        }
