from __future__ import annotations

import ast
import runpy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingService,
)
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
    ObjectiveLearningExperienceRecord,
)
from app.platform.events.event_store import PlatformEventStore
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


def _canonical_source():
    """
    Reuse the canonical verified customer-support source fixture that
    already exercises the product-owned extraction contract.
    """

    namespace = runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_recording.py"
    )

    return namespace["_source"]()


class StaticCanonicalSourceLoader:
    def __init__(self, source) -> None:
        self.source = source
        self.calls = []

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
                "resolution_record_id": (resolution_record_id),
                "tenant_id": tenant_id,
            }
        )

        return self.source


@pytest.mark.asyncio
async def test_customer_support_objective_learning_lifecycle_e2e():
    """
    Prove the safe objective-learning lifecycle across real persistence:

    canonical verified customer-support source
      -> extraction
      -> idempotent experience persistence
      -> authenticated aggregation
      -> deterministic proposal
      -> append-only approval
      -> approved advisory retrieval

    Approval remains informational and does not activate behavior.
    """

    user_id = uuid4()
    reviewer_id = uuid4()
    other_user_id = uuid4()

    base_source = _canonical_source()

    async with SessionLocal() as db:
        source_event = await PlatformEventStore(db).append(
            user_id=user_id,
            event_type=("customer_service.support.outcome.evaluated"),
            source="test.slice_7h",
            payload={
                "objective_ref": (base_source.objective_ref),
                "evaluation_ref": (base_source.evaluation_ref),
            },
            meta={
                "slice": "7h",
                "informational_only": True,
            },
            commit=True,
        )

        resolution_assessment = ObjectiveResolutionAssessment(
            objective=ObjectiveReference(
                namespace=(base_source.objective_namespace),
                objective_type=(base_source.objective_type),
                objective_ref=(base_source.objective_ref),
                objective_version=(base_source.objective_version),
            ),
            source=ObjectiveResolutionSource(
                outcome_ref=(base_source.outcome_ref),
                outcome_version=1,
                evaluation_ref=(base_source.evaluation_ref),
                evaluation_version=1,
                workflow_run_id=(base_source.workflow_run_id),
            ),
            status=(ObjectiveResolutionStatus.ACHIEVED),
            reason_code=("verified_customer_support_outcome"),
            summary=("Customer-support objective was verified as achieved."),
            confidence=1.0,
            is_terminal=True,
            operations=(
                ObjectiveOperationResolution(
                    operation_ref=("verified-support-operation"),
                    operation_type=("customer_support_resolution"),
                    status=(ObjectiveOperationStatus.ACHIEVED),
                    required=True,
                    reason_code=("verified_outcome"),
                    summary=("Required support operation was verified."),
                    evidence_refs=tuple(base_source.evidence_refs),
                ),
            ),
            metadata={
                "slice": "7h",
                "informational_only": True,
                "authorizes_execution": False,
            },
        )

        resolution_write = await ObjectiveResolutionService(db).record_assessment(
            source_event_id=source_event.id,
            user_id=user_id,
            tenant_id=base_source.tenant_id,
            assessment=resolution_assessment,
            projection_version=1,
        )

        assert resolution_write.created is True
        assert resolution_write.event_id is not None

        resolution_record_id = resolution_write.record.id

        source = base_source.model_copy(
            update={
                "user_id": str(user_id),
                "resolution_record_id": str(resolution_record_id),
            }
        )

        loader = StaticCanonicalSourceLoader(source)

        experience_repository = ObjectiveLearningExperienceRepository(db)

        recording_service = CustomerSupportObjectiveLearningRecordingService(
            db,
            source_loader=loader,
            repository=experience_repository,
        )

        first_recording = await recording_service.record_for_resolution(
            user_id=user_id,
            resolution_record_id=(resolution_record_id),
        )

        repeated_recording = await recording_service.record_for_resolution(
            user_id=user_id,
            resolution_record_id=(resolution_record_id),
        )

        assert first_recording.created is True
        assert repeated_recording.created is False
        assert first_recording.record.id == repeated_recording.record.id
        assert first_recording.experience == repeated_recording.experience
        assert first_recording.experience.informational_only is True
        assert first_recording.experience.authorizes_execution is False

        experience_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == user_id,
                ObjectiveLearningExperienceRecord.resolution_record_id
                == resolution_record_id,
            )
        )

        assert experience_count == 1

        aggregation_now = datetime.now(timezone.utc) + timedelta(seconds=1)

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
            tenant_id=(first_recording.record.tenant_id),
            objective_namespace=(first_recording.record.objective_namespace),
            objective_type=(first_recording.record.objective_type),
            now=aggregation_now,
        )

        assert len(summaries) == 1

        aggregation = summaries[0]

        assert aggregation.total_experiences == 1
        assert aggregation.informational_only is True
        assert aggregation.authorizes_execution is False
        assert (
            aggregation.objective_namespace
            == first_recording.record.objective_namespace
        )
        assert aggregation.objective_type == first_recording.record.objective_type

        lifecycle = ObjectiveLearningLifecycleOperations(
            db=db,
            repository=(ObjectiveLearningCandidateRepository(db)),
            factory=ObjectiveLearningCandidateFactory(
                policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
            ),
        )

        first_proposal = await lifecycle.propose(
            user_id=user_id,
            aggregation=aggregation,
            proposed_at=aggregation_now,
        )

        repeated_proposal = await lifecycle.propose(
            user_id=user_id,
            aggregation=aggregation,
            proposed_at=aggregation_now,
        )

        assert first_proposal.created is True
        assert repeated_proposal.created is False
        assert first_proposal.candidate == repeated_proposal.candidate
        assert first_proposal.candidate.candidate_version == 1
        assert first_proposal.candidate.status.value == "validated"
        assert first_proposal.candidate.approval_status.value == "pending"

        candidate_id = first_proposal.candidate.candidate_id

        other_latest = await lifecycle.get_latest(
            user_id=other_user_id,
            candidate_id=candidate_id,
        )

        assert other_latest is None

        approved = await lifecycle.review(
            user_id=user_id,
            candidate_id=candidate_id,
            reviewed_by_user_id=reviewer_id,
            request=(
                ObjectiveLearningCandidateReviewRequest(
                    decision=(ObjectiveLearningReviewDecision.APPROVE),
                    reason=("Verified customer-support evidence accepted."),
                    reviewed_at=(aggregation_now + timedelta(seconds=1)),
                )
            ),
        )

        assert approved is not None
        assert approved.candidate_version == 2
        assert approved.status.value == "approved"
        assert approved.approval_status.value == "approved"
        assert approved.reviewed_by_user_id == reviewer_id
        assert approved.informational_only is True
        assert approved.affects_ranking is False
        assert approved.affects_capability_selection is False
        assert approved.affects_business_plan is False
        assert approved.selects_provider is False
        assert approved.authorizes_execution is False
        assert approved.bypasses_approval is False
        assert approved.bypasses_verification is False

        history = await lifecycle.history(
            user_id=user_id,
            candidate_id=candidate_id,
        )

        assert [item.candidate_version for item in history] == [1, 2]

        assert history[0].status.value == "validated"
        assert history[0].approval_status.value == ("pending")
        assert history[0].reviewed_at is None
        assert history[1] == approved

        revision_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(
                ObjectiveLearningCandidateRevisionRecord.user_id == user_id,
                ObjectiveLearningCandidateRevisionRecord.candidate_id == candidate_id,
            )
        )

        assert revision_count == 2

        approved_service = ObjectiveLearningApprovedInsightService(
            db=db,
            repository=(ObjectiveLearningCandidateRepository(db)),
        )

        insight = await approved_service.get_approved(
            user_id=user_id,
            candidate_id=candidate_id,
        )

        assert insight is not None
        assert insight.provenance.candidate_id == candidate_id
        assert insight.provenance.candidate_version == 2
        assert insight.decision == "approved"
        assert insight.recommended_review == approved.review_reason
        assert insight.validity_scope == aggregation.validity_scope
        assert insight.summary_confidence == aggregation.summary_confidence
        assert insight.informational_only is True
        assert insight.affects_ranking is False
        assert insight.affects_capability_selection is False
        assert insight.affects_business_plan is False
        assert insight.selects_provider is False
        assert insight.authorizes_execution is False
        assert insight.bypasses_approval is False
        assert insight.bypasses_verification is False

        other_insight = await approved_service.get_approved(
            user_id=other_user_id,
            candidate_id=candidate_id,
        )

        assert other_insight is None

        approved_list = await approved_service.list_approved(
            user_id=user_id,
            tenant_id=aggregation.tenant_id,
            objective_namespace=(aggregation.objective_namespace),
            objective_type=(aggregation.objective_type),
        )

        assert [
            item.provenance.candidate_id
            for item in approved_list
            if (item.provenance.candidate_id == candidate_id)
        ] == [candidate_id]

        other_list = await approved_service.list_approved(
            user_id=other_user_id,
            tenant_id=aggregation.tenant_id,
            objective_namespace=(aggregation.objective_namespace),
            objective_type=(aggregation.objective_type),
        )

        assert all(item.provenance.candidate_id != candidate_id for item in other_list)

        assert len(loader.calls) == 2
        assert all(call["user_id"] == user_id for call in loader.calls)
        assert all(
            call["resolution_record_id"] == resolution_record_id
            for call in loader.calls
        )


def test_e2e_proof_adds_no_production_activation():
    """
    The end-to-end slice is proof only. Production learning services
    must still have no Planner, execution, event, job, or node wiring.
    """

    production_paths = [
        Path(
            "app/domains/customer_service/services/support/learning/"
            "customer_support_objective_learning_recording.py"
        ),
        Path("app/runtime/objectives/learning/lifecycle_operations.py"),
        Path("app/runtime/objectives/learning/approved_insight_service.py"),
    ]

    forbidden_import_prefixes = (
        "app.agents_runtime",
        "app.tcos",
        "app.runtime.nodes",
        "app.runtime.engine",
        "app.platform.jobs",
        "app.platform.events",
    )

    forbidden_calls = {
        "publish",
        "enqueue",
        "dispatch",
        "activate",
        "rank",
        "rerank",
        "authorize",
        "execute",
        "run",
        "resume",
    }

    for path in production_paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imports: set[str] = set()
        calls: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
            elif isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(
                    node.func,
                    ast.Attribute,
                ):
                    calls.add(node.func.attr)

        assert not any(
            module.startswith(forbidden_import_prefixes) for module in imports
        )

        assert not (forbidden_calls & calls), (
            path,
            forbidden_calls & calls,
        )
