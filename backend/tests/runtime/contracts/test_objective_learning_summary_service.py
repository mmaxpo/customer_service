from __future__ import annotations

from copy import deepcopy
from datetime import (
    datetime,
    timedelta,
    timezone,
)
import runpy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.objectives.learning import (
    ObjectiveLearningAggregationPolicy,
    ObjectiveLearningSummaryService,
    objective_learning_aggregation_key,
)


NOW = datetime(
    2026,
    8,
    4,
    8,
    0,
    tzinfo=timezone.utc,
)


class FakeObjectiveLearningRepository:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    async def list_for_aggregation(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        end = kwargs["now"] or NOW
        start = end - timedelta(hours=kwargs["window_hours"])

        return start, end, list(self.rows)


def _payload(
    *,
    objective_ref="review-plan-1",
    resolution_record_id="resolution-1",
    outcome_ref="outcome-1",
    evaluation_ref="evaluation-1",
    workflow_run_id="workflow-run-1",
):
    namespace = runpy.run_path(
        "tests/runtime/contracts/test_objective_learning_aggregation.py"
    )

    return namespace["_payload"](
        objective_ref=objective_ref,
        resolution_record_id=(resolution_record_id),
        outcome_ref=outcome_ref,
        evaluation_ref=evaluation_ref,
        workflow_run_id=workflow_run_id,
    )


def _record(payload):
    return SimpleNamespace(experience_json=payload)


@pytest.mark.asyncio
async def test_summary_service_groups_exact_scopes():
    first = _payload()

    same_scope = _payload(
        objective_ref="review-plan-2",
        resolution_record_id="resolution-2",
        outcome_ref="outcome-2",
        evaluation_ref="evaluation-2",
        workflow_run_id="workflow-run-2",
    )

    different_scope = deepcopy(same_scope)
    different_scope["validity_scope"]["workflow_version"] = "different"

    service = ObjectiveLearningSummaryService(
        db=SimpleNamespace(),
        repository=(
            FakeObjectiveLearningRepository(
                [
                    _record(different_scope),
                    _record(same_scope),
                    _record(first),
                ]
            )
        ),
        aggregation_policy=(
            ObjectiveLearningAggregationPolicy(minimum_effective_sample_size=1)
        ),
    )

    summaries = await service.summarize(
        user_id=uuid4(),
        window_hours=24,
        now=NOW,
    )

    assert len(summaries) == 2
    assert sorted(summary.total_experiences for summary in summaries) == [1, 2]

    assert {summary.scope_fingerprint for summary in summaries} == {
        objective_learning_aggregation_key(first),
        objective_learning_aggregation_key(different_scope),
    }


@pytest.mark.asyncio
async def test_summary_service_returns_deterministic_order():
    first = _payload()
    first["validity_scope"]["tenant_id"] = "tenant-b"

    second = _payload(
        objective_ref="review-plan-2",
        resolution_record_id="resolution-2",
        outcome_ref="outcome-2",
        evaluation_ref="evaluation-2",
        workflow_run_id="workflow-run-2",
    )
    second["validity_scope"]["tenant_id"] = "tenant-a"

    service = ObjectiveLearningSummaryService(
        db=SimpleNamespace(),
        repository=(
            FakeObjectiveLearningRepository(
                [
                    _record(first),
                    _record(second),
                ]
            )
        ),
    )

    summaries = await service.summarize(
        user_id=uuid4(),
        now=NOW,
    )

    assert [summary.tenant_id for summary in summaries] == [
        "tenant-a",
        "tenant-b",
    ]


@pytest.mark.asyncio
async def test_summary_service_returns_empty_list():
    repository = FakeObjectiveLearningRepository([])

    service = ObjectiveLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
    )

    summaries = await service.summarize(
        user_id=uuid4(),
        now=NOW,
    )

    assert summaries == []
    assert len(repository.calls) == 1


@pytest.mark.asyncio
async def test_summary_service_forwards_full_scope():
    user_id = uuid4()
    repository = FakeObjectiveLearningRepository([])

    service = ObjectiveLearningSummaryService(
        db=SimpleNamespace(),
        repository=repository,
    )

    summaries = await service.summarize(
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

    assert summaries == []

    assert repository.calls == [
        {
            "user_id": user_id,
            "window_hours": 24,
            "tenant_id": "tenant-a",
            "objective_namespace": "support",
            "objective_type": "refund",
            "objective_version": 2,
            "schema_ref": "schema.a",
            "profile_ref": "profile.a",
            "profile_version": 3,
            "extractor_ref": "extractor.a",
            "extractor_version": 4,
            "now": NOW,
        }
    ]


@pytest.mark.asyncio
async def test_summary_service_injects_policy():
    first = _payload()

    service = ObjectiveLearningSummaryService(
        db=SimpleNamespace(),
        repository=(FakeObjectiveLearningRepository([_record(first)])),
        aggregation_policy=(
            ObjectiveLearningAggregationPolicy(minimum_effective_sample_size=1)
        ),
    )

    summaries = await service.summarize(
        user_id=uuid4(),
        now=NOW,
    )

    assert len(summaries) == 1
    assert summaries[0].minimum_effective_sample_size == 1


def test_aggregation_key_ignores_instance_metadata():
    first = _payload()

    second = _payload(
        objective_ref="review-plan-2",
        resolution_record_id="resolution-2",
        outcome_ref="outcome-2",
        evaluation_ref="evaluation-2",
        workflow_run_id="workflow-run-2",
    )

    assert objective_learning_aggregation_key(
        first
    ) == objective_learning_aggregation_key(second)


def test_aggregation_key_preserves_reusable_scope():
    first = _payload()
    second = deepcopy(first)

    second["validity_scope"]["workflow_version"] = "different"

    assert objective_learning_aggregation_key(
        first
    ) != objective_learning_aggregation_key(second)


def test_summary_service_has_read_only_boundary():
    import ast
    from pathlib import Path

    path = Path('app/runtime/objectives/learning/summary_service.py')

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

    assert "list_for_aggregation" in calls
    assert "summarize" in calls

    for forbidden in (
        "commit",
        "flush",
        "add",
        "publish",
        "enqueue",
        "dispatch",
        "rank",
        "rerank",
        "activate",
        "authorize",
    ):
        assert forbidden not in calls


def test_summary_service_surface_is_focused():
    import ast
    from pathlib import Path

    path = Path('app/runtime/objectives/learning/summary_service.py')

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    service = next(
        node
        for node in tree.body
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "ObjectiveLearningSummaryService"
        )
    )

    methods = {
        node.name
        for node in service.body
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
        "summarize",
    }
