from __future__ import annotations

from datetime import datetime, timedelta, timezone
import runpy
from uuid import uuid4

import pytest
from sqlalchemy import update

from app.core.session import SessionLocal
from app.models.models import (
    ObjectiveLearningExperienceRecord,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningExperienceRepository,
)


NOW = datetime(
    2026,
    8,
    4,
    8,
    0,
    tzinfo=timezone.utc,
)


def _repository_test_helpers():
    return runpy.run_path(
        "tests/runtime/contracts/test_objective_learning_repository.py"
    )


async def _record(
    db,
    *,
    user_id,
    tenant_id="tenant-1",
    objective_namespace=("customer_service.support"),
    objective_type="multi_operation",
    objective_version=1,
    schema_ref=("customer_service.support.objective_learning_experience.v1"),
    profile_ref=("customer_service.support.multi_operation"),
    profile_version=1,
    extractor_ref=("customer_service.support.objective_learning_extractor"),
    extractor_version=1,
    created_at=NOW - timedelta(hours=1),
):
    helpers = _repository_test_helpers()

    resolution = await helpers["_resolution"](
        db,
        user_id=user_id,
        objective_ref=f"review-plan-{uuid4()}",
    )

    values = helpers["_experience_values"](
        user_id=user_id,
        resolution_record_id=resolution.id,
        profile_version=profile_version,
        extractor_version=extractor_version,
    )

    values.update(
        {
            "tenant_id": tenant_id,
            "objective_namespace": (objective_namespace),
            "objective_type": objective_type,
            "objective_version": (objective_version),
            "schema_ref": schema_ref,
            "profile_ref": profile_ref,
            "profile_version": (profile_version),
            "extractor_ref": extractor_ref,
            "extractor_version": (extractor_version),
        }
    )

    experience = dict(values["experience"])
    experience.update(
        {
            "schema_ref": schema_ref,
            "profile_ref": profile_ref,
            "profile_version": (profile_version),
            "extractor_ref": extractor_ref,
            "extractor_version": (extractor_version),
        }
    )

    validity_scope = dict(values["validity_scope"])
    validity_scope.update(
        {
            "tenant_id": tenant_id,
            "objective_namespace": (objective_namespace),
            "objective_type": objective_type,
            "objective_version": (objective_version),
        }
    )

    experience["validity_scope"] = validity_scope

    values["experience"] = experience
    values["validity_scope"] = validity_scope

    row, created = await ObjectiveLearningExperienceRepository(db).record(
        **values,
        commit=True,
    )

    assert created is True

    await db.execute(
        update(ObjectiveLearningExperienceRecord)
        .where(ObjectiveLearningExperienceRecord.id == row.id)
        .values(created_at=created_at)
    )
    await db.commit()
    await db.refresh(row)

    return row


@pytest.mark.asyncio
async def test_query_is_user_scoped_and_bounded():
    owner_id = uuid4()
    other_id = uuid4()

    async with SessionLocal() as db:
        included = await _record(
            db,
            user_id=owner_id,
            created_at=(NOW - timedelta(hours=2)),
        )

        await _record(
            db,
            user_id=owner_id,
            created_at=(NOW - timedelta(hours=25)),
        )

        await _record(
            db,
            user_id=other_id,
            created_at=(NOW - timedelta(hours=2)),
        )

        (
            window_start,
            window_end,
            rows,
        ) = await ObjectiveLearningExperienceRepository(db).list_for_aggregation(
            user_id=owner_id,
            window_hours=24,
            now=NOW,
        )

    assert window_start == (NOW - timedelta(hours=24))
    assert window_end == NOW
    assert [row.id for row in rows] == [included.id]


@pytest.mark.asyncio
async def test_query_uses_half_open_window():
    user_id = uuid4()

    async with SessionLocal() as db:
        at_start = await _record(
            db,
            user_id=user_id,
            created_at=(NOW - timedelta(hours=24)),
        )

        await _record(
            db,
            user_id=user_id,
            created_at=NOW,
        )

        _, _, rows = await ObjectiveLearningExperienceRepository(
            db
        ).list_for_aggregation(
            user_id=user_id,
            window_hours=24,
            now=NOW,
        )

    assert [row.id for row in rows] == [at_start.id]


@pytest.mark.asyncio
async def test_query_orders_by_created_at_then_id():
    user_id = uuid4()
    timestamp = NOW - timedelta(hours=1)

    async with SessionLocal() as db:
        first = await _record(
            db,
            user_id=user_id,
            created_at=timestamp,
        )
        second = await _record(
            db,
            user_id=user_id,
            created_at=timestamp,
        )

        _, _, rows = await ObjectiveLearningExperienceRepository(
            db
        ).list_for_aggregation(
            user_id=user_id,
            window_hours=24,
            now=NOW,
        )

    expected = sorted(
        [first, second],
        key=lambda row: (
            row.created_at,
            row.id,
        ),
    )

    assert [row.id for row in rows] == [row.id for row in expected]


@pytest.mark.asyncio
async def test_query_applies_exact_filters():
    user_id = uuid4()

    async with SessionLocal() as db:
        matching = await _record(
            db,
            user_id=user_id,
            tenant_id="tenant-a",
            objective_namespace="support",
            objective_type="refund",
            objective_version=2,
            schema_ref="schema.a",
            profile_ref="profile.a",
            profile_version=3,
            extractor_ref="extractor.a",
            extractor_version=4,
        )

        await _record(
            db,
            user_id=user_id,
            tenant_id="tenant-b",
            objective_namespace="support",
            objective_type="refund",
            objective_version=2,
            schema_ref="schema.a",
            profile_ref="profile.a",
            profile_version=3,
            extractor_ref="extractor.a",
            extractor_version=4,
        )

        _, _, rows = await ObjectiveLearningExperienceRepository(
            db
        ).list_for_aggregation(
            user_id=user_id,
            window_hours=24,
            tenant_id="tenant-a",
            objective_namespace="support",
            objective_type="refund",
            objective_version=2,
            schema_ref="schema.a",
            profile_ref="profile.a",
            profile_version=3,
            extractor_ref="extractor.a",
            extractor_version=4,
            now=NOW,
        )

    assert [row.id for row in rows] == [matching.id]


@pytest.mark.asyncio
async def test_query_accepts_naive_now_as_utc():
    user_id = uuid4()
    naive_now = NOW.replace(tzinfo=None)

    async with SessionLocal() as db:
        await _record(
            db,
            user_id=user_id,
        )

        (
            window_start,
            window_end,
            rows,
        ) = await ObjectiveLearningExperienceRepository(db).list_for_aggregation(
            user_id=user_id,
            window_hours=24,
            now=naive_now,
        )

    assert window_end.tzinfo == timezone.utc
    assert window_end == NOW
    assert window_start == (NOW - timedelta(hours=24))
    assert len(rows) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "window_hours",
    [
        0,
        -1,
        8761,
    ],
)
async def test_query_rejects_invalid_window(
    window_hours,
):
    async with SessionLocal() as db:
        repository = ObjectiveLearningExperienceRepository(db)

        with pytest.raises(
            ValueError,
            match="between 1 and 8760",
        ):
            await repository.list_for_aggregation(
                user_id=uuid4(),
                window_hours=window_hours,
                now=NOW,
            )


@pytest.mark.asyncio
async def test_query_normalizes_user_id():
    user_id = uuid4()

    async with SessionLocal() as db:
        row = await _record(
            db,
            user_id=user_id,
        )

        _, _, rows = await ObjectiveLearningExperienceRepository(
            db
        ).list_for_aggregation(
            user_id=str(user_id),
            window_hours=24,
            now=NOW,
        )

    assert [item.id for item in rows] == [row.id]


def test_query_has_no_aggregation_or_behavioral_wiring():
    import ast
    from pathlib import Path

    path = Path('app/runtime/objectives/learning/repository.py')

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    repository = next(
        node
        for node in tree.body
        if (
            isinstance(node, ast.ClassDef)
            and node.name == ("ObjectiveLearningExperienceRepository")
        )
    )

    method = next(
        node
        for node in repository.body
        if (
            isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "list_for_aggregation"
        )
    )

    method_source = (
        ast.get_source_segment(
            source,
            method,
        )
        or ""
    )

    calls: set[str] = set()

    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(
            node.func,
            ast.Attribute,
        ):
            calls.add(node.func.attr)

    assert "execute" in calls
    assert "commit" not in calls
    assert "flush" not in calls
    assert "add" not in calls
    assert "publish" not in calls
    assert "enqueue" not in calls
    assert "dispatch" not in calls
    assert "summarize" not in calls
    assert "aggregate" not in calls

    assert "user_id" in method_source
    assert "created_at" in method_source
    assert ".asc()" in method_source
