from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.models.models import (
    ObjectiveRepairExecutionRecord,
)
from app.runtime.objectives.repair.repository import (
    ObjectiveRepairExecutionRepository,
)


def _repository(*, records=()):
    scalars = Mock()
    scalars.all.return_value = list(records)

    result = Mock()
    result.scalars.return_value = scalars

    db = SimpleNamespace(execute=AsyncMock(return_value=result))

    repository = ObjectiveRepairExecutionRepository(db)

    return SimpleNamespace(
        repository=repository,
        db=db,
        result=result,
        scalars=scalars,
    )


@pytest.mark.asyncio
async def test_list_for_resolution_returns_query_results():
    first = SimpleNamespace(
        id=uuid4(),
        attempt_number=1,
    )
    second = SimpleNamespace(
        id=uuid4(),
        attempt_number=2,
    )

    deps = _repository(records=(first, second))

    user_id = uuid4()
    resolution_record_id = uuid4()

    records = await deps.repository.list_for_resolution(
        user_id=user_id,
        resolution_record_id=resolution_record_id,
    )

    assert records == [first, second]
    deps.db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_for_resolution_is_user_scoped():
    deps = _repository()

    user_id = uuid4()
    resolution_record_id = uuid4()

    await deps.repository.list_for_resolution(
        user_id=user_id,
        resolution_record_id=resolution_record_id,
    )

    statement = deps.db.execute.await_args.args[0]
    compiled = statement.compile()

    params = set(compiled.params.values())

    assert user_id in params
    assert resolution_record_id in params


@pytest.mark.asyncio
async def test_list_for_resolution_orders_oldest_attempt_first():
    deps = _repository()

    await deps.repository.list_for_resolution(
        user_id=uuid4(),
        resolution_record_id=uuid4(),
    )

    statement = deps.db.execute.await_args.args[0]

    order_by = tuple(str(item) for item in statement._order_by_clauses)

    assert order_by == (
        ("objective_repair_executions.attempt_number ASC"),
        ("objective_repair_executions.created_at ASC"),
        "objective_repair_executions.id ASC",
    )


@pytest.mark.asyncio
async def test_list_for_resolution_applies_requested_limit():
    deps = _repository()

    await deps.repository.list_for_resolution(
        user_id=uuid4(),
        resolution_record_id=uuid4(),
        limit=37,
    )

    statement = deps.db.execute.await_args.args[0]
    compiled = statement.compile()

    assert 37 in compiled.params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit",
    (
        0,
        -1,
        501,
    ),
)
async def test_list_for_resolution_rejects_invalid_limit(
    limit,
):
    deps = _repository()

    with pytest.raises(
        ValueError,
        match="limit must be between 1 and 500",
    ):
        await deps.repository.list_for_resolution(
            user_id=uuid4(),
            resolution_record_id=uuid4(),
            limit=limit,
        )

    deps.db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_for_resolution_accepts_boundary_limits():
    for limit in (1, 500):
        deps = _repository()

        await deps.repository.list_for_resolution(
            user_id=uuid4(),
            resolution_record_id=uuid4(),
            limit=limit,
        )

        deps.db.execute.assert_awaited_once()


def test_history_method_is_defined_before_latest_query():
    names = tuple(ObjectiveRepairExecutionRepository.__dict__)

    assert names.index("list_for_resolution") < (
        names.index("get_latest_for_resolution")
    )


def test_history_method_returns_repair_record_contract():
    annotation = ObjectiveRepairExecutionRepository.list_for_resolution.__annotations__[
        "return"
    ]

    assert "ObjectiveRepairExecutionRecord" in str(annotation)


def test_history_query_does_not_change_model_contract():
    assert ObjectiveRepairExecutionRecord.__tablename__ == (
        "objective_repair_executions"
    )
