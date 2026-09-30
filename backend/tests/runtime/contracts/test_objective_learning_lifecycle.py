from __future__ import annotations

from datetime import datetime, timezone
import runpy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.learning import (
    ObjectiveLearningApprovalStatus,
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateStatus,
    ObjectiveLearningAggregator,
)


NOW = datetime(
    2026,
    8,
    4,
    8,
    0,
    tzinfo=timezone.utc,
)


def _aggregation(
    *,
    minimum_effective_sample_size=0.5,
):
    namespace = runpy.run_path(
        "tests/runtime/contracts/test_objective_learning_aggregation.py"
    )

    payload = namespace["_payload"]()

    return ObjectiveLearningAggregator(
        policy=namespace["ObjectiveLearningAggregationPolicy"](
            minimum_effective_sample_size=(minimum_effective_sample_size)
        )
    ).summarize(experiences=[payload])


def test_valid_evidence_creates_pending_candidate():
    aggregation = _aggregation()

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )

    assert candidate.candidate_version == 1
    assert candidate.status == (ObjectiveLearningCandidateStatus.VALIDATED)
    assert candidate.approval_status == (ObjectiveLearningApprovalStatus.PENDING)
    assert candidate.validation_passed is True
    assert candidate.validated_at == NOW
    assert candidate.blocking_reasons == ("explicit_approval_required",)
    assert candidate.informational_only is True
    assert candidate.authorizes_execution is False


def test_insufficient_evidence_creates_blocked_candidate():
    aggregation = _aggregation(minimum_effective_sample_size=5.0)

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )

    assert candidate.status == (ObjectiveLearningCandidateStatus.BLOCKED)
    assert candidate.validation_passed is False
    assert candidate.validated_at is None
    assert "evidence_sufficient" in (candidate.blocking_reasons)


def test_candidate_id_is_deterministic():
    aggregation = _aggregation()

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    first = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )
    second = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )

    assert first.candidate_id == second.candidate_id
    assert first.evidence.scope_fingerprint == aggregation.scope_fingerprint


def test_approved_review_creates_version_two():
    aggregation = _aggregation()

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )
    reviewer_id = uuid4()

    approved = factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=reviewer_id,
        reason="Evidence accepted.",
        reviewed_at=NOW,
    )

    assert approved.candidate_id == (candidate.candidate_id)
    assert approved.candidate_version == 2
    assert approved.status == (ObjectiveLearningCandidateStatus.APPROVED)
    assert approved.approval_status == (ObjectiveLearningApprovalStatus.APPROVED)
    assert approved.reviewed_by_user_id == (reviewer_id)
    assert approved.review_reason == ("Evidence accepted.")
    assert approved.blocking_reasons == ()
    assert approved.authorizes_execution is False


def test_rejected_review_records_rejection():
    aggregation = _aggregation()

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )

    rejected = factory.review(
        candidate=candidate,
        approved=False,
        reviewed_by_user_id=uuid4(),
        reason="Evidence not accepted.",
        reviewed_at=NOW,
    )

    assert rejected.candidate_version == 2
    assert rejected.status == (ObjectiveLearningCandidateStatus.REJECTED)
    assert rejected.approval_status == (ObjectiveLearningApprovalStatus.REJECTED)
    assert rejected.blocking_reasons == ("approval_rejected",)


def test_blocked_candidate_cannot_be_reviewed():
    aggregation = _aggregation(minimum_effective_sample_size=5.0)

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match="pending validated",
    ):
        factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="Should fail.",
            reviewed_at=NOW,
        )


def test_review_cannot_be_repeated():
    aggregation = _aggregation()

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )

    approved = factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Approved.",
        reviewed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match="pending validated",
    ):
        factory.review(
            candidate=approved,
            approved=False,
            reviewed_by_user_id=uuid4(),
            reason="Cannot repeat.",
            reviewed_at=NOW,
        )


def test_review_requires_reason():
    aggregation = _aggregation()

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW,
    )

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason=" ",
            reviewed_at=NOW,
        )


def test_naive_timestamps_are_normalized_to_utc():
    aggregation = _aggregation()

    factory = ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )

    candidate = factory.propose(
        aggregation=aggregation,
        proposed_at=NOW.replace(tzinfo=None),
    )

    assert candidate.proposed_at.tzinfo == (timezone.utc)


@pytest.mark.parametrize(
    "field_name",
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
def test_policy_rejects_behavioral_authority(
    field_name,
):
    with pytest.raises(
        ValidationError,
        match="cannot alter planning or execution",
    ):
        ObjectiveLearningCandidatePolicy(
            **{
                field_name: True,
            }
        )


def test_lifecycle_has_no_persistence_or_wiring():
    import ast
    from pathlib import Path

    path = Path('app/runtime/objectives/learning/lifecycle.py')

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

    assert not any(item.startswith("sqlalchemy") for item in imports)

    assert not any(item.startswith("app.domains.customer_service") for item in imports)

    for forbidden in (
        "commit",
        "flush",
        "add",
        "execute",
        "publish",
        "enqueue",
        "dispatch",
        "rank",
        "activate",
        "authorize",
    ):
        assert forbidden not in calls


def test_lifecycle_surface_is_focused():
    import ast
    from pathlib import Path

    path = Path('app/runtime/objectives/learning/lifecycle.py')

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    factory = next(
        node
        for node in tree.body
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "ObjectiveLearningCandidateFactory"
        )
    )

    methods = {
        node.name
        for node in factory.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    assert methods == {
        "__init__",
        "propose",
        "review",
        "_validation_checks",
    }
