from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import (
    ObjectiveLearningExperienceRecord,
)
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningExperienceConflictError,
    ObjectiveLearningExperienceRepository,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionRepository,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)


def _assessment(
    *,
    evaluation_ref: str,
    objective_ref: str,
) -> ObjectiveResolutionAssessment:
    return ObjectiveResolutionAssessment(
        objective=ObjectiveReference(
            namespace="customer_service.support",
            objective_type="multi_operation",
            objective_ref=objective_ref,
            objective_version=1,
        ),
        source=ObjectiveResolutionSource(
            outcome_ref=f"outcome:{uuid4()}",
            outcome_version=1,
            evaluation_ref=evaluation_ref,
            evaluation_version=1,
            workflow_run_id=f"run:{uuid4()}",
        ),
        status=(ObjectiveResolutionStatus.ACHIEVED),
        reason_code="objective_achieved",
        summary="The objective was achieved.",
        confidence=0.95,
        is_terminal=True,
        operations=(
            ObjectiveOperationResolution(
                operation_ref="operation-1",
                operation_type="whole_refund",
                status=(ObjectiveOperationStatus.ACHIEVED),
            ),
        ),
        metadata={"safe": True},
    )


async def _resolution(
    db,
    *,
    user_id: UUID,
    objective_ref: str,
):
    event = await PlatformEventStore(db).append(
        user_id=user_id,
        event_type="example.objective.evaluated",
        source="test",
        payload={},
        meta={},
        commit=True,
    )

    assessment = _assessment(
        evaluation_ref=str(uuid4()),
        objective_ref=objective_ref,
    )

    row, created = await ObjectiveResolutionRepository(db).record(
        source_event_id=event.id,
        user_id=user_id,
        tenant_id="tenant-1",
        assessment=assessment,
        commit=True,
    )

    assert created is True

    return row


def _experience_values(
    *,
    user_id: UUID,
    resolution_record_id: UUID,
    profile_version: int = 1,
    extractor_version: int = 1,
    summary: str = "Verified experience.",
):
    experience = {
        "schema_ref": ("customer_service.support.objective_learning_experience.v1"),
        "profile_ref": ("customer_service.support.multi_operation"),
        "profile_version": profile_version,
        "extractor_ref": ("customer_service.support.objective_learning_extractor"),
        "extractor_version": extractor_version,
        "user_id": str(user_id),
        "objective_ref": "review-plan-1",
        "resolution_record_id": (str(resolution_record_id)),
        "outcome_ref": "outcome-1",
        "evaluation_ref": "evaluation-1",
        "validity_scope": {
            "tenant_id": "tenant-1",
            "objective_namespace": ("customer_service.support"),
            "objective_type": "multi_operation",
            "objective_version": 1,
            "capability_ids": [
                "ecommerce.orders.get",
                "ecommerce.orders.manage",
            ],
            "provider_ids": [
                "commerce-provider",
            ],
            "provider_refs": [
                "commerce-provider.order_read",
                "commerce-provider.order_action",
            ],
            "workflow_template_ref": ("customer-support-review"),
            "workflow_version": "4",
            "planner_ref": None,
            "planner_policy_version": None,
            "versioned_refs": [],
            "metadata": {
                "workflow_run_id": ("workflow-run-1"),
            },
        },
        "dimensions": [
            {
                "key": "required_evidence",
                "value": {
                    "summary": summary,
                },
            },
            {
                "key": "repair_strategy",
                "value": {
                    "strategy": "retry_verified",
                },
            },
        ],
        "evidence_refs": [
            "outcome:outcome-1",
            "evaluation:evaluation-1",
        ],
        "informational_only": True,
        "authorizes_execution": False,
        "metadata": {
            "review_plan_id": "review-plan-1",
        },
    }

    return {
        "user_id": user_id,
        "tenant_id": "tenant-1",
        "resolution_record_id": (resolution_record_id),
        "objective_namespace": ("customer_service.support"),
        "objective_type": "multi_operation",
        "objective_ref": "review-plan-1",
        "objective_version": 1,
        "schema_ref": experience["schema_ref"],
        "profile_ref": experience["profile_ref"],
        "profile_version": profile_version,
        "extractor_ref": experience["extractor_ref"],
        "extractor_version": extractor_version,
        "outcome_ref": "outcome-1",
        "evaluation_ref": "evaluation-1",
        "workflow_run_id": "workflow-run-1",
        "dimension_keys": [item["key"] for item in experience["dimensions"]],
        "evidence_refs": experience["evidence_refs"],
        "validity_scope": experience["validity_scope"],
        "experience": experience,
        "informational_only": True,
        "authorizes_execution": False,
    }


@pytest.mark.asyncio
async def test_repository_records_and_round_trips():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=user_id,
            objective_ref="review-plan-1",
        )

        repository = ObjectiveLearningExperienceRepository(db)

        values = _experience_values(
            user_id=user_id,
            resolution_record_id=resolution.id,
        )

        row, created = await repository.record(
            **values,
            commit=True,
        )

        restored = repository.experience_from_record(row)

    assert created is True
    assert restored == values["experience"]
    assert row.user_id == user_id
    assert row.resolution_record_id == resolution.id
    assert row.dimension_keys_json == [
        "required_evidence",
        "repair_strategy",
    ]
    assert row.informational_only is True
    assert row.authorizes_execution is False


@pytest.mark.asyncio
async def test_duplicate_semantic_identity_is_idempotent():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=user_id,
            objective_ref="review-plan-duplicate",
        )

        repository = ObjectiveLearningExperienceRepository(db)
        values = _experience_values(
            user_id=user_id,
            resolution_record_id=resolution.id,
        )

        first, first_created = await repository.record(
            **values,
            commit=True,
        )
        second, second_created = await repository.record(
            **deepcopy(values),
            commit=True,
        )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id


@pytest.mark.asyncio
async def test_same_identity_with_changed_facts_conflicts():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=user_id,
            objective_ref="review-plan-conflict",
        )

        repository = ObjectiveLearningExperienceRepository(db)
        original = _experience_values(
            user_id=user_id,
            resolution_record_id=resolution.id,
            summary="Original evidence.",
        )
        changed = _experience_values(
            user_id=user_id,
            resolution_record_id=resolution.id,
            summary="Changed evidence.",
        )

        await repository.record(
            **original,
            commit=True,
        )

        with pytest.raises(
            ObjectiveLearningExperienceConflictError,
            match="different experience facts",
        ):
            await repository.record(
                **changed,
                commit=True,
            )


@pytest.mark.asyncio
async def test_new_extractor_version_creates_new_record():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=user_id,
            objective_ref="review-plan-version",
        )

        repository = ObjectiveLearningExperienceRepository(db)

        first, first_created = await repository.record(
            **_experience_values(
                user_id=user_id,
                resolution_record_id=(resolution.id),
                extractor_version=1,
            ),
            commit=True,
        )
        second, second_created = await repository.record(
            **_experience_values(
                user_id=user_id,
                resolution_record_id=(resolution.id),
                extractor_version=2,
            ),
            commit=True,
        )

    assert first_created is True
    assert second_created is True
    assert first.id != second.id


@pytest.mark.asyncio
async def test_reads_are_scoped_to_authenticated_user():
    owner_id = uuid4()
    other_user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=owner_id,
            objective_ref="review-plan-scope",
        )

        repository = ObjectiveLearningExperienceRepository(db)
        row, _ = await repository.record(
            **_experience_values(
                user_id=owner_id,
                resolution_record_id=resolution.id,
            ),
            commit=True,
        )

        owned = await repository.get_for_user(
            user_id=owner_id,
            record_id=row.id,
        )
        hidden = await repository.get_for_user(
            user_id=other_user_id,
            record_id=row.id,
        )
        hidden_history = await repository.list_for_resolution(
            user_id=other_user_id,
            resolution_record_id=(resolution.id),
        )

    assert owned is not None
    assert owned.id == row.id
    assert hidden is None
    assert hidden_history == []


@pytest.mark.asyncio
async def test_resolution_history_is_deterministic():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=user_id,
            objective_ref="review-plan-history",
        )

        repository = ObjectiveLearningExperienceRepository(db)

        third, _ = await repository.record(
            **_experience_values(
                user_id=user_id,
                resolution_record_id=resolution.id,
                profile_version=2,
                extractor_version=1,
            ),
            commit=True,
        )
        second, _ = await repository.record(
            **_experience_values(
                user_id=user_id,
                resolution_record_id=resolution.id,
                profile_version=1,
                extractor_version=2,
            ),
            commit=True,
        )
        first, _ = await repository.record(
            **_experience_values(
                user_id=user_id,
                resolution_record_id=resolution.id,
                profile_version=1,
                extractor_version=1,
            ),
            commit=True,
        )

        history = await repository.list_for_resolution(
            user_id=user_id,
            resolution_record_id=(resolution.id),
        )

    assert [item.id for item in history] == [
        first.id,
        second.id,
        third.id,
    ]


@pytest.mark.asyncio
async def test_commit_false_flushes_without_owning_commit():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=user_id,
            objective_ref="review-plan-rollback",
        )

        repository = ObjectiveLearningExperienceRepository(db)
        values = _experience_values(
            user_id=user_id,
            resolution_record_id=resolution.id,
        )

        row, created = await repository.record(
            **values,
            commit=False,
        )

        visible_in_transaction = await repository.get_for_user(
            user_id=user_id,
            record_id=row.id,
        )

        assert created is True
        assert visible_in_transaction is not None

        row_id = row.id

        await db.rollback()

    async with SessionLocal() as db:
        persisted = await db.scalar(
            select(ObjectiveLearningExperienceRecord).where(
                ObjectiveLearningExperienceRecord.id == row_id
            )
        )

    assert persisted is None


@pytest.mark.asyncio
async def test_safety_invariants_are_rejected_before_write():
    user_id = uuid4()

    async with SessionLocal() as db:
        resolution = await _resolution(
            db,
            user_id=user_id,
            objective_ref="review-plan-safety",
        )

        repository = ObjectiveLearningExperienceRepository(db)
        values = _experience_values(
            user_id=user_id,
            resolution_record_id=resolution.id,
        )

        unsafe = {
            **values,
            "authorizes_execution": True,
        }

        with pytest.raises(
            ValueError,
            match="cannot authorize execution",
        ):
            await repository.record(
                **unsafe,
                commit=False,
            )

        noninformational = {
            **values,
            "informational_only": False,
        }

        with pytest.raises(
            ValueError,
            match="must remain informational only",
        ):
            await repository.record(
                **noninformational,
                commit=False,
            )


def test_repository_has_no_product_or_behavioral_wiring():
    from pathlib import Path

    source = Path('app/runtime/objectives/learning/repository.py').read_text(
        encoding="utf-8"
    )

    forbidden = (
        "app.domains.customer_service",
        "PlatformEventPublisher",
        "JobService",
        "enqueue(",
        "publish(",
        "dispatch(",
        "planner.",
        "ranking",
        "extract_customer_support",
    )

    for value in forbidden:
        assert value not in source

    assert "on_conflict_do_nothing" in source
    assert "commit: bool = False" in source
    assert "await self.db.flush()" in source
