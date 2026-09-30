from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.learning import (
    BusinessLearningApprovedInsightService,
    BusinessLearningInsightCandidate,
    BusinessLearningInsightCandidateFactory,
)
from tests.runtime.contracts.test_business_learning_insight_candidates import (
    NOW,
    trusted_report,
)


def approved_candidate():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report(),
        proposed_at=NOW,
    )

    return factory.review(
        candidate=candidate,
        approved=True,
        reviewed_by_user_id=uuid4(),
        reason="Evidence accepted.",
        reviewed_at=NOW,
    )


class FakeRepository:
    def __init__(
        self,
        candidates,
    ):
        self.candidates = {
            item.candidate_id: item
            for item in candidates
        }
        self.list_calls = []
        self.get_calls = []

    async def list_latest_for_user(
        self,
        **kwargs,
    ):
        self.list_calls.append(kwargs)

        return [
            SimpleNamespace(
                candidate_json=(
                    candidate.model_dump(
                        mode="json"
                    )
                )
            )
            for candidate in (
                self.candidates.values()
            )
        ]

    async def get_latest_for_user(
        self,
        **kwargs,
    ):
        self.get_calls.append(kwargs)

        candidate = self.candidates.get(
            kwargs["candidate_id"]
        )

        if candidate is None:
            return None

        return SimpleNamespace(
            candidate_json=(
                candidate.model_dump(
                    mode="json"
                )
            )
        )

    @staticmethod
    def deserialize(
        row,
    ):
        return (
            BusinessLearningInsightCandidate
            .model_validate(
                row.candidate_json
            )
        )


@pytest.mark.asyncio
async def test_list_projects_only_approved_filter():
    user_id = uuid4()
    candidate = approved_candidate()
    repository = FakeRepository(
        [candidate]
    )

    service = (
        BusinessLearningApprovedInsightService(
            db=SimpleNamespace(),
            repository=repository,
        )
    )

    insights = await service.list_approved(
        user_id=user_id,
        tenant_id="tenant-a",
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        decision="approved",
        limit=25,
        offset=5,
    )

    assert len(insights) == 1
    assert (
        insights[0].provenance.candidate_id
        == candidate.candidate_id
    )

    call = repository.list_calls[0]

    assert call["user_id"] == user_id
    assert call["status"] == "approved"
    assert call["approval_status"] == (
        "approved"
    )
    assert call["limit"] == 25
    assert call["offset"] == 5


@pytest.mark.asyncio
async def test_get_returns_approved_insight():
    user_id = uuid4()
    candidate = approved_candidate()

    service = (
        BusinessLearningApprovedInsightService(
            db=SimpleNamespace(),
            repository=FakeRepository(
                [candidate]
            ),
        )
    )

    insight = await service.get_approved(
        user_id=user_id,
        candidate_id=candidate.candidate_id,
    )

    assert insight is not None
    assert (
        insight.provenance.candidate_id
        == candidate.candidate_id
    )


@pytest.mark.asyncio
async def test_get_hides_nonapproved_candidate():
    factory = (
        BusinessLearningInsightCandidateFactory()
    )
    candidate = factory.propose(
        report=trusted_report(),
        proposed_at=NOW,
    )

    service = (
        BusinessLearningApprovedInsightService(
            db=SimpleNamespace(),
            repository=FakeRepository(
                [candidate]
            ),
        )
    )

    insight = await service.get_approved(
        user_id=uuid4(),
        candidate_id=candidate.candidate_id,
    )

    assert insight is None


@pytest.mark.asyncio
async def test_get_is_user_scoped():
    user_id = uuid4()
    candidate = approved_candidate()
    repository = FakeRepository(
        [candidate]
    )

    service = (
        BusinessLearningApprovedInsightService(
            db=SimpleNamespace(),
            repository=repository,
        )
    )

    await service.get_approved(
        user_id=user_id,
        candidate_id=candidate.candidate_id,
    )

    assert (
        repository.get_calls[0]["user_id"]
        == user_id
    )


@pytest.mark.asyncio
async def test_missing_candidate_returns_none():
    service = (
        BusinessLearningApprovedInsightService(
            db=SimpleNamespace(),
            repository=FakeRepository([]),
        )
    )

    assert (
        await service.get_approved(
            user_id=uuid4(),
            candidate_id=uuid4(),
        )
        is None
    )
