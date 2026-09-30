from __future__ import annotations

from datetime import datetime, timezone
import runpy
from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.objectives.learning import (
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateRepository,
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


@pytest.mark.asyncio
async def test_repository_appends_and_reads_history():
    user_id = uuid4()
    reviewer_id = uuid4()
    factory = _factory()

    candidate = factory.propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        first = await repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        approved = factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=reviewer_id,
            reason="Confirmed.",
            reviewed_at=NOW,
        )

        second = await repository.append_revision(
            user_id=user_id,
            candidate=approved,
        )

        history = await repository.list_history_for_user(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )

        latest = await repository.get_latest_for_user(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
        )

        assert first.version == 1
        assert second.version == 2
        assert [row.version for row in history] == [1, 2]
        assert latest is not None
        assert latest.status == "approved"
        assert latest.approval_status == "approved"
        assert latest.informational_only is True
        assert latest.authorizes_execution is False
        assert repository.deserialize(latest) == approved


@pytest.mark.asyncio
async def test_repository_rejects_version_gap():
    candidate = (
        _factory()
        .propose(
            aggregation=_aggregation(),
            proposed_at=NOW,
        )
        .model_copy(update={"candidate_version": 2})
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        with pytest.raises(
            ValueError,
            match="next append-only revision",
        ):
            await repository.append_revision(
                user_id=uuid4(),
                candidate=candidate,
            )

        await db.rollback()


@pytest.mark.asyncio
async def test_duplicate_revision_is_rejected():
    user_id = uuid4()
    candidate = _factory().propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        await repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        with pytest.raises(
            ValueError,
            match="next append-only revision",
        ):
            await repository.append_revision(
                user_id=user_id,
                candidate=candidate,
            )

        await db.rollback()


@pytest.mark.asyncio
async def test_repository_enforces_cross_user_isolation():
    owner_id = uuid4()
    other_id = uuid4()
    candidate = _factory().propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        await repository.append_revision(
            user_id=owner_id,
            candidate=candidate,
        )

        assert (
            await repository.get_latest_for_user(
                user_id=other_id,
                candidate_id=candidate.candidate_id,
            )
            is None
        )

        assert (
            await repository.list_history_for_user(
                user_id=other_id,
                candidate_id=candidate.candidate_id,
            )
            == []
        )


@pytest.mark.asyncio
async def test_same_deterministic_candidate_isolated_by_user():
    first_user_id = uuid4()
    second_user_id = uuid4()

    candidate = _factory().propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        first = await repository.append_revision(
            user_id=first_user_id,
            candidate=candidate,
        )

        second = await repository.append_revision(
            user_id=second_user_id,
            candidate=candidate,
        )

        assert first.candidate_id == second.candidate_id
        assert first.version == 1
        assert second.version == 1
        assert first.user_id == first_user_id
        assert second.user_id == second_user_id

        first_latest = await repository.get_latest_for_user(
            user_id=first_user_id,
            candidate_id=candidate.candidate_id,
        )

        second_latest = await repository.get_latest_for_user(
            user_id=second_user_id,
            candidate_id=candidate.candidate_id,
        )

        assert first_latest is not None
        assert second_latest is not None
        assert first_latest.user_id == first_user_id
        assert second_latest.user_id == second_user_id


@pytest.mark.asyncio
async def test_get_latest_by_fingerprint_is_scoped():
    owner_id = uuid4()
    other_id = uuid4()
    candidate = _factory().propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        await repository.append_revision(
            user_id=owner_id,
            candidate=candidate,
        )

        owner = await repository.get_latest_by_fingerprint_for_user(
            user_id=owner_id,
            scope_fingerprint=(candidate.evidence.scope_fingerprint),
        )

        other = await repository.get_latest_by_fingerprint_for_user(
            user_id=other_id,
            scope_fingerprint=(candidate.evidence.scope_fingerprint),
        )

        assert owner is not None
        assert other is None


@pytest.mark.asyncio
async def test_get_revision_returns_exact_version():
    user_id = uuid4()
    factory = _factory()
    candidate = factory.propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        await repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        approved = factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="Confirmed.",
            reviewed_at=NOW,
        )

        await repository.append_revision(
            user_id=user_id,
            candidate=approved,
        )

        first = await repository.get_revision_for_user(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
            version=1,
        )

        second = await repository.get_revision_for_user(
            user_id=user_id,
            candidate_id=candidate.candidate_id,
            version=2,
        )

        assert first is not None
        assert second is not None
        assert first.status == "validated"
        assert second.status == "approved"


@pytest.mark.asyncio
async def test_list_latest_returns_latest_revision():
    user_id = uuid4()
    factory = _factory()
    candidate = factory.propose(
        aggregation=_aggregation(),
        proposed_at=NOW,
    )

    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        await repository.append_revision(
            user_id=user_id,
            candidate=candidate,
        )

        approved = factory.review(
            candidate=candidate,
            approved=True,
            reviewed_by_user_id=uuid4(),
            reason="Confirmed.",
            reviewed_at=NOW,
        )

        await repository.append_revision(
            user_id=user_id,
            candidate=approved,
        )

        rows = await repository.list_latest_for_user(
            user_id=user_id,
            objective_namespace=(candidate.evidence.objective_namespace),
            status="approved",
            approval_status="approved",
            validation_passed=True,
        )

        matching = [row for row in rows if row.candidate_id == candidate.candidate_id]

        assert len(matching) == 1
        assert matching[0].version == 2


@pytest.mark.asyncio
async def test_list_latest_validates_pagination():
    async with SessionLocal() as db:
        repository = ObjectiveLearningCandidateRepository(db)

        with pytest.raises(
            ValueError,
            match="between 1 and 500",
        ):
            await repository.list_latest_for_user(
                user_id=uuid4(),
                limit=0,
            )

        with pytest.raises(
            ValueError,
            match="offset must be >= 0",
        ):
            await repository.list_latest_for_user(
                user_id=uuid4(),
                offset=-1,
            )


def test_repository_is_infrastructure_only():
    import ast
    from pathlib import Path

    path = Path('app/runtime/objectives/learning/lifecycle_repository.py')

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

    assert "execute" in calls
    assert "commit" in calls
    assert "flush" in calls
    assert "add" in calls

    for forbidden in (
        "publish",
        "enqueue",
        "dispatch",
        "propose",
        "review",
        "rank",
        "activate",
        "authorize",
    ):
        assert forbidden not in calls
