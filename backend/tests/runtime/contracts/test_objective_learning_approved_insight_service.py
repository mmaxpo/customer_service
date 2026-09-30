from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.learning import (
    ObjectiveLearningApprovedInsight,
    ObjectiveLearningApprovedInsightProjection,
    ObjectiveLearningApprovedInsightService,
    ObjectiveLearningCandidate,
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningAggregator,
)


NOW = datetime(
    2026,
    8,
    4,
    10,
    0,
    tzinfo=timezone.utc,
)


def _aggregation():
    namespace = runpy.run_path(
        "tests/runtime/contracts/test_objective_learning_aggregation.py"
    )

    return ObjectiveLearningAggregator(
        policy=namespace["ObjectiveLearningAggregationPolicy"](
            minimum_effective_sample_size=0.5
        )
    ).summarize(experiences=[namespace["_payload"]()])


def approved_candidate():
    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    return factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Evidence accepted for review.",
        reviewed_at=NOW,
    )


def _row(candidate):
    return SimpleNamespace(candidate_json=candidate.model_dump(mode="json"))


class FakeRepository:
    def __init__(self, candidates):
        self.candidates = {
            candidate.candidate_id: candidate for candidate in candidates
        }
        self.list_calls = []
        self.get_calls = []

    async def list_latest_for_user(
        self,
        **kwargs,
    ):
        self.list_calls.append(kwargs)

        return [
            _row(candidate)
            for candidate in self.candidates.values()
            if (
                candidate.status.value == kwargs["status"]
                and candidate.approval_status.value == kwargs["approval_status"]
                and candidate.validation_passed == kwargs["validation_passed"]
            )
        ]

    async def get_latest_for_user(
        self,
        **kwargs,
    ):
        self.get_calls.append(kwargs)

        candidate = self.candidates.get(kwargs["candidate_id"])

        if candidate is None:
            return None

        return _row(candidate)

    @staticmethod
    def deserialize(
        row,
    ) -> ObjectiveLearningCandidate:
        return ObjectiveLearningCandidate.model_validate(row.candidate_json)


@pytest.mark.asyncio
async def test_list_approved_enforces_all_filters():
    user_id = uuid4()
    candidate = approved_candidate()
    repository = FakeRepository([candidate])

    service = ObjectiveLearningApprovedInsightService(
        db=SimpleNamespace(),
        repository=repository,
    )

    insights = await service.list_approved(
        user_id=user_id,
        tenant_id="tenant-a",
        objective_namespace=(candidate.evidence.objective_namespace),
        objective_type=(candidate.evidence.objective_type),
        limit=25,
        offset=5,
    )

    assert len(insights) == 1
    assert insights[0].provenance.candidate_id == candidate.candidate_id

    call = repository.list_calls[0]

    assert call["user_id"] == user_id
    assert call["status"] == "approved"
    assert call["approval_status"] == "approved"
    assert call["validation_passed"] is True
    assert call["limit"] == 25
    assert call["offset"] == 5


@pytest.mark.asyncio
async def test_get_returns_safe_approved_projection():
    candidate = approved_candidate()

    service = ObjectiveLearningApprovedInsightService(
        db=SimpleNamespace(),
        repository=FakeRepository([candidate]),
    )

    insight = await service.get_approved(
        user_id=uuid4(),
        candidate_id=candidate.candidate_id,
    )

    assert insight is not None
    assert insight.provenance.candidate_id == candidate.candidate_id
    assert insight.provenance.candidate_version == 2
    assert insight.decision == "approved"
    assert insight.informational_only is True
    assert insight.authorizes_execution is False
    assert insight.affects_ranking is False
    assert insight.selects_provider is False


@pytest.mark.asyncio
async def test_get_hides_nonapproved_candidate():
    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    service = ObjectiveLearningApprovedInsightService(
        db=SimpleNamespace(),
        repository=FakeRepository([candidate]),
    )

    result = await service.get_approved(
        user_id=uuid4(),
        candidate_id=candidate.candidate_id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_missing_candidate_returns_none():
    service = ObjectiveLearningApprovedInsightService(
        db=SimpleNamespace(),
        repository=FakeRepository([]),
    )

    assert (
        await service.get_approved(
            user_id=uuid4(),
            candidate_id=uuid4(),
        )
        is None
    )


@pytest.mark.asyncio
async def test_get_is_authenticated_user_scoped():
    user_id = uuid4()
    candidate = approved_candidate()
    repository = FakeRepository([candidate])

    service = ObjectiveLearningApprovedInsightService(
        db=SimpleNamespace(),
        repository=repository,
    )

    await service.get_approved(
        user_id=user_id,
        candidate_id=candidate.candidate_id,
    )

    assert repository.get_calls[0]["user_id"] == user_id


def test_projection_preserves_scope_evidence_and_provenance():
    candidate = approved_candidate()

    insight = ObjectiveLearningApprovedInsightProjection.from_candidate(candidate)

    aggregation = candidate.evidence.aggregation_json

    assert insight.validity_scope == aggregation["validity_scope"]
    assert insight.summary_confidence == aggregation["summary_confidence"]
    assert insight.provenance.scope_fingerprint == candidate.evidence.scope_fingerprint
    assert insight.provenance.policy_ref == candidate.policy_ref
    assert insight.recommended_review == candidate.review_reason


def test_projection_rejects_nonapproved_candidate():
    candidate = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    ).propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match="Only approved",
    ):
        (ObjectiveLearningApprovedInsightProjection.from_candidate(candidate))


@pytest.mark.parametrize(
    "field",
    [
        "affects_ranking",
        "affects_capability_selection",
        "affects_business_plan",
        "selects_provider",
        "authorizes_execution",
        "bypasses_approval",
        "bypasses_verification",
    ],
)
def test_insight_rejects_behavioral_authority(
    field,
):
    insight = ObjectiveLearningApprovedInsightProjection.from_candidate(
        approved_candidate()
    )

    payload = insight.model_dump(mode="python")
    payload[field] = True

    with pytest.raises(
        ValidationError,
        match="cannot alter planning or execution",
    ):
        ObjectiveLearningApprovedInsight(**payload)


def test_projection_has_no_activation_fields():
    insight = ObjectiveLearningApprovedInsightProjection.from_candidate(
        approved_candidate()
    )

    payload = insight.model_dump(mode="json")

    assert "promotion_id" not in payload
    assert "promotion_target" not in payload
    assert "active" not in payload
    assert "revoked" not in payload
    assert "recommended_behavior" not in payload

    assert "recommended_review" in payload
    assert "limitations" in payload
    assert "provenance" in payload


def test_service_has_no_behavioral_or_write_wiring():
    path = Path('app/runtime/objectives/learning/approved_insight_service.py')

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
        value.startswith("app.domains.customer_service") for value in imports
    )

    for required in (
        "list_latest_for_user",
        "get_latest_for_user",
        "deserialize",
        "from_candidate",
    ):
        assert required in calls

    for forbidden in (
        "append_revision",
        "add",
        "flush",
        "commit",
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
    ):
        assert forbidden not in calls
