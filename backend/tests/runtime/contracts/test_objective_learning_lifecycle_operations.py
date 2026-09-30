from __future__ import annotations

from datetime import datetime, timezone
import ast
from pathlib import Path
import runpy
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.runtime.objectives.learning import (
    ObjectiveLearningCandidate,
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateReviewRequest,
    ObjectiveLearningLifecycleOperations,
    ObjectiveLearningReviewDecision,
    ObjectiveLearningAggregator,
)


NOW = datetime(
    2026,
    8,
    4,
    9,
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


def _factory():
    return ObjectiveLearningCandidateFactory(
        policy=ObjectiveLearningCandidatePolicy(minimum_summary_confidence=0.0)
    )


def _row(
    candidate: ObjectiveLearningCandidate,
):
    return SimpleNamespace(
        candidate_id=candidate.candidate_id,
        version=candidate.candidate_version,
        candidate_json=candidate.model_dump(mode="json"),
    )


class FakeRepository:
    def __init__(self) -> None:
        self.rows: dict[
            tuple[UUID, UUID],
            list[SimpleNamespace],
        ] = {}

        self.fingerprints: dict[
            tuple[UUID, str],
            SimpleNamespace,
        ] = {}

        self.append_calls = []
        self.fingerprint_calls = []
        self.get_calls = []
        self.history_calls = []
        self.list_calls = []

    async def append_revision(
        self,
        *,
        user_id,
        candidate,
    ):
        self.append_calls.append(
            {
                "user_id": user_id,
                "candidate": candidate,
            }
        )

        row = _row(candidate)

        key = (
            user_id,
            candidate.candidate_id,
        )

        self.rows.setdefault(key, []).append(row)

        self.fingerprints[
            (
                user_id,
                candidate.evidence.scope_fingerprint,
            )
        ] = row

        return row

    async def get_latest_by_fingerprint_for_user(
        self,
        *,
        user_id,
        scope_fingerprint,
    ):
        self.fingerprint_calls.append(
            {
                "user_id": user_id,
                "scope_fingerprint": (scope_fingerprint),
            }
        )

        return self.fingerprints.get(
            (
                user_id,
                scope_fingerprint,
            )
        )

    async def get_latest_for_user(
        self,
        *,
        user_id,
        candidate_id,
    ):
        self.get_calls.append(
            {
                "user_id": user_id,
                "candidate_id": candidate_id,
            }
        )

        rows = self.rows.get(
            (
                user_id,
                candidate_id,
            ),
            [],
        )

        return rows[-1] if rows else None

    async def list_history_for_user(
        self,
        *,
        user_id,
        candidate_id,
    ):
        self.history_calls.append(
            {
                "user_id": user_id,
                "candidate_id": candidate_id,
            }
        )

        return list(
            self.rows.get(
                (
                    user_id,
                    candidate_id,
                ),
                [],
            )
        )

    async def list_latest_for_user(
        self,
        **kwargs,
    ):
        self.list_calls.append(kwargs)

        user_id = kwargs["user_id"]

        return [
            rows[-1]
            for (owner_id, _), rows in (self.rows.items())
            if owner_id == user_id and rows
        ]

    @staticmethod
    def deserialize(
        row,
    ) -> ObjectiveLearningCandidate:
        return ObjectiveLearningCandidate.model_validate(row.candidate_json)


def _operations(
    repository: FakeRepository,
):
    return ObjectiveLearningLifecycleOperations(
        db=SimpleNamespace(),
        repository=repository,
        factory=_factory(),
    )


@pytest.mark.asyncio
async def test_propose_creates_first_revision():
    user_id = uuid4()
    repository = FakeRepository()

    result = await _operations(repository).propose(
        user_id=user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    assert result.created is True
    assert result.created_candidates == 1
    assert result.existing_candidates == 0
    assert result.item.created is True
    assert result.candidate.candidate_version == 1
    assert result.candidate.status.value == "validated"
    assert result.candidate.approval_status.value == ("pending")

    assert repository.append_calls[0]["user_id"] == user_id


@pytest.mark.asyncio
async def test_propose_is_idempotent_by_user_fingerprint():
    user_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    first = await operations.propose(
        user_id=user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    second = await operations.propose(
        user_id=user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    assert first.created is True
    assert second.created is False
    assert second.candidate == first.candidate
    assert len(repository.append_calls) == 1


@pytest.mark.asyncio
async def test_same_fingerprint_is_independent_per_user():
    first_user_id = uuid4()
    second_user_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    first = await operations.propose(
        user_id=first_user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    second = await operations.propose(
        user_id=second_user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    assert first.created is True
    assert second.created is True
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert len(repository.append_calls) == 2


@pytest.mark.asyncio
async def test_reads_are_authenticated_user_scoped():
    owner_id = uuid4()
    other_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    created = await operations.propose(
        user_id=owner_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    candidate_id = created.candidate.candidate_id

    assert (
        await operations.get_latest(
            user_id=other_id,
            candidate_id=candidate_id,
        )
        is None
    )

    assert (
        await operations.history(
            user_id=other_id,
            candidate_id=candidate_id,
        )
        == []
    )

    assert (
        await operations.list_latest(
            user_id=other_id,
        )
        == []
    )


@pytest.mark.asyncio
async def test_list_latest_forwards_filters():
    user_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    await operations.list_latest(
        user_id=user_id,
        tenant_id="tenant-a",
        objective_namespace=("customer_service.support"),
        objective_type="multi_operation",
        objective_version=1,
        schema_ref="schema.v1",
        profile_ref="profile.v1",
        profile_version=1,
        extractor_ref="extractor.v1",
        extractor_version=1,
        status="validated",
        approval_status="pending",
        validation_passed=True,
        limit=25,
        offset=5,
    )

    call = repository.list_calls[0]

    assert call["user_id"] == user_id
    assert call["tenant_id"] == "tenant-a"
    assert call["status"] == "validated"
    assert call["approval_status"] == "pending"
    assert call["validation_passed"] is True
    assert call["limit"] == 25
    assert call["offset"] == 5


@pytest.mark.asyncio
async def test_review_approves_latest_owned_candidate():
    user_id = uuid4()
    reviewer_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    created = await operations.propose(
        user_id=user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    reviewed = await operations.review(
        user_id=user_id,
        candidate_id=(created.candidate.candidate_id),
        reviewed_by_user_id=reviewer_id,
        request=(
            ObjectiveLearningCandidateReviewRequest(
                decision=(ObjectiveLearningReviewDecision.APPROVE),
                reason=" Evidence accepted. ",
                reviewed_at=NOW,
            )
        ),
    )

    assert reviewed is not None
    assert reviewed.candidate_version == 2
    assert reviewed.status.value == "approved"
    assert reviewed.approval_status.value == ("approved")
    assert reviewed.review_reason == ("Evidence accepted.")
    assert reviewed.reviewed_by_user_id == reviewer_id
    assert reviewed.informational_only is True
    assert reviewed.authorizes_execution is False

    assert len(repository.append_calls) == 2


@pytest.mark.asyncio
async def test_review_rejects_latest_owned_candidate():
    user_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    created = await operations.propose(
        user_id=user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    reviewed = await operations.review(
        user_id=user_id,
        candidate_id=(created.candidate.candidate_id),
        reviewed_by_user_id=uuid4(),
        request=(
            ObjectiveLearningCandidateReviewRequest(
                decision=(ObjectiveLearningReviewDecision.REJECT),
                reason="Not suitable.",
                reviewed_at=NOW,
            )
        ),
    )

    assert reviewed is not None
    assert reviewed.status.value == "rejected"
    assert reviewed.approval_status.value == ("rejected")
    assert reviewed.blocking_reasons == ("approval_rejected",)


@pytest.mark.asyncio
async def test_review_missing_or_cross_user_returns_none():
    owner_id = uuid4()
    other_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    created = await operations.propose(
        user_id=owner_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    result = await operations.review(
        user_id=other_id,
        candidate_id=(created.candidate.candidate_id),
        reviewed_by_user_id=other_id,
        request=(
            ObjectiveLearningCandidateReviewRequest(
                decision=(ObjectiveLearningReviewDecision.APPROVE),
                reason="Accept.",
                reviewed_at=NOW,
            )
        ),
    )

    assert result is None
    assert len(repository.append_calls) == 1


@pytest.mark.asyncio
async def test_reviewed_candidate_cannot_be_reviewed_again():
    user_id = uuid4()
    repository = FakeRepository()
    operations = _operations(repository)

    created = await operations.propose(
        user_id=user_id,
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    request = ObjectiveLearningCandidateReviewRequest(
        decision=(ObjectiveLearningReviewDecision.APPROVE),
        reason="Accept.",
        reviewed_at=NOW,
    )

    await operations.review(
        user_id=user_id,
        candidate_id=(created.candidate.candidate_id),
        reviewed_by_user_id=uuid4(),
        request=request,
    )

    with pytest.raises(
        ValueError,
        match=("Only a pending validated objective learning candidate can be reviewed"),
    ):
        await operations.review(
            user_id=user_id,
            candidate_id=(created.candidate.candidate_id),
            reviewed_by_user_id=uuid4(),
            request=request,
        )


def test_review_request_rejects_empty_reason():
    with pytest.raises(
        ValidationError,
        match="must not be empty",
    ):
        ObjectiveLearningCandidateReviewRequest(
            decision=(ObjectiveLearningReviewDecision.APPROVE),
            reason="   ",
        )


def test_operations_have_no_behavioral_wiring():
    path = Path('app/runtime/objectives/learning/lifecycle_operations.py')

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

    assert not any(item.startswith("app.domains.customer_service") for item in imports)

    for required in (
        "propose",
        "review",
        "append_revision",
        "get_latest_for_user",
        "list_latest_for_user",
        "list_history_for_user",
        "deserialize",
    ):
        assert required in calls

    for forbidden in (
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
