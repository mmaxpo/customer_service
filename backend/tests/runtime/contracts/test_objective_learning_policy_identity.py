from __future__ import annotations

import runpy
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.models.models import (
    ObjectiveLearningCandidateRevisionRecord,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningCandidateFactory,
    ObjectiveLearningCandidatePolicy,
    ObjectiveLearningCandidateRepository,
    ObjectiveLearningLifecycleOperations,
)


def _contract_helpers():
    return runpy.run_path(
        "tests/runtime/contracts/test_objective_learning_lifecycle_operations.py"
    )


def _operations(
    db,
    *,
    policy_version: int,
) -> ObjectiveLearningLifecycleOperations:
    return ObjectiveLearningLifecycleOperations(
        db=db,
        repository=(ObjectiveLearningCandidateRepository(db)),
        factory=ObjectiveLearningCandidateFactory(
            policy=ObjectiveLearningCandidatePolicy(
                policy_ref=("customer_service.support.candidate_policy"),
                policy_version=policy_version,
                minimum_summary_confidence=0.0,
            )
        ),
    )


@pytest.mark.asyncio
async def test_policy_version_is_part_of_candidate_idempotency():
    helpers = _contract_helpers()
    aggregation = helpers["_aggregation"]()

    user_id = uuid4()

    async with SessionLocal() as db:
        version_one = _operations(
            db,
            policy_version=1,
        )

        first_v1 = await version_one.propose(
            user_id=user_id,
            aggregation=aggregation,
        )

        repeated_v1 = await version_one.propose(
            user_id=user_id,
            aggregation=aggregation,
        )

        version_two = _operations(
            db,
            policy_version=2,
        )

        first_v2 = await version_two.propose(
            user_id=user_id,
            aggregation=aggregation,
        )

        repeated_v2 = await version_two.propose(
            user_id=user_id,
            aggregation=aggregation,
        )

        assert first_v1.created is True
        assert repeated_v1.created is False
        assert repeated_v1.candidate == first_v1.candidate

        assert first_v2.created is True
        assert repeated_v2.created is False
        assert repeated_v2.candidate == first_v2.candidate

        assert (
            first_v1.candidate.evidence.scope_fingerprint
            == first_v2.candidate.evidence.scope_fingerprint
        )

        assert first_v1.candidate.candidate_id != first_v2.candidate.candidate_id

        assert first_v1.candidate.policy_version == 1
        assert first_v2.candidate.policy_version == 2

        rows = list(
            (
                await db.execute(
                    select(ObjectiveLearningCandidateRevisionRecord)
                    .where(ObjectiveLearningCandidateRevisionRecord.user_id == user_id)
                    .order_by(
                        ObjectiveLearningCandidateRevisionRecord.policy_version.asc()
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(rows) == 2
        assert [row.policy_version for row in rows] == [1, 2]

        assert {row.candidate_id for row in rows} == {
            first_v1.candidate.candidate_id,
            first_v2.candidate.candidate_id,
        }

        assert {row.scope_fingerprint for row in rows} == {
            aggregation.scope_fingerprint,
        }

        revision_count = await db.scalar(
            select(func.count())
            .select_from(ObjectiveLearningCandidateRevisionRecord)
            .where(ObjectiveLearningCandidateRevisionRecord.user_id == user_id)
        )

        assert revision_count == 2
