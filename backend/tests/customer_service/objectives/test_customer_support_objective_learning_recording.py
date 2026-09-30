from __future__ import annotations

import runpy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domains.customer_service.services.support.learning.customer_support_objective_learning_recording import (
    CustomerSupportObjectiveLearningRecordingResult,
    CustomerSupportObjectiveLearningRecordingService,
)
from app.domains.customer_service.services.support.learning.objective_learning_extraction import (
    CustomerSupportObjectiveLearningExperience,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    build_customer_support_objective_learning_profile,
)


def _source():
    namespace = runpy.run_path(
        "tests/customer_service/objectives/"
        "test_customer_support_objective_learning_extraction.py"
    )

    return namespace["source"]()


def _record():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        informational_only=True,
        authorizes_execution=False,
    )


def _service(
    *,
    source,
    record=None,
    created=True,
    db=None,
):
    db = db or SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    loader = SimpleNamespace(load_for_resolution=AsyncMock(return_value=source))

    repository = SimpleNamespace(
        record=AsyncMock(
            return_value=(
                record or _record(),
                created,
            )
        )
    )

    service = CustomerSupportObjectiveLearningRecordingService(
        db,
        source_loader=loader,
        repository=repository,
        profile=(build_customer_support_objective_learning_profile()),
    )

    return SimpleNamespace(
        service=service,
        db=db,
        loader=loader,
        repository=repository,
    )


@pytest.mark.asyncio
async def test_service_loads_extracts_maps_and_commits():
    source = _source()
    record = _record()
    user_id = uuid4()
    resolution_record_id = uuid4()

    deps = _service(
        source=source,
        record=record,
        created=True,
    )

    result = await deps.service.record_for_resolution(
        user_id=user_id,
        resolution_record_id=(resolution_record_id),
        tenant_id="tenant-1",
    )

    assert isinstance(
        result,
        CustomerSupportObjectiveLearningRecordingResult,
    )
    assert result.record is record
    assert result.created is True
    assert result.source is source
    assert isinstance(
        result.experience,
        CustomerSupportObjectiveLearningExperience,
    )

    deps.loader.load_for_resolution.assert_awaited_once_with(
        user_id=user_id,
        resolution_record_id=resolution_record_id,
        tenant_id="tenant-1",
    )

    deps.repository.record.assert_awaited_once()

    values = deps.repository.record.await_args.kwargs

    payload = result.experience.model_dump(mode="json")
    scope = payload["validity_scope"]

    assert values["user_id"] == payload["user_id"]
    assert values["tenant_id"] == (scope["tenant_id"])
    assert values["resolution_record_id"] == (payload["resolution_record_id"])
    assert values["objective_namespace"] == (scope["objective_namespace"])
    assert values["objective_type"] == (scope["objective_type"])
    assert values["objective_ref"] == (payload["objective_ref"])
    assert values["objective_version"] == (scope["objective_version"])
    assert values["schema_ref"] == (payload["schema_ref"])
    assert values["profile_ref"] == (payload["profile_ref"])
    assert values["profile_version"] == (payload["profile_version"])
    assert values["extractor_ref"] == (payload["extractor_ref"])
    assert values["extractor_version"] == (payload["extractor_version"])
    assert values["outcome_ref"] == (payload["outcome_ref"])
    assert values["evaluation_ref"] == (payload["evaluation_ref"])
    assert values["workflow_run_id"] == (scope["metadata"]["workflow_run_id"])
    assert values["dimension_keys"] == [item["key"] for item in payload["dimensions"]]
    assert values["evidence_refs"] == (payload["evidence_refs"])
    assert values["validity_scope"] == scope
    assert values["experience"] == payload
    assert values["informational_only"] is True
    assert values["authorizes_execution"] is False
    assert values["commit"] is False

    deps.db.commit.assert_awaited_once_with()
    deps.db.refresh.assert_awaited_once_with(record)
    deps.db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_recording_returns_existing_truth():
    source = _source()
    record = _record()

    deps = _service(
        source=source,
        record=record,
        created=False,
    )

    result = await deps.service.record_for_resolution(
        user_id=uuid4(),
        resolution_record_id=uuid4(),
    )

    assert result.record is record
    assert result.created is False
    assert result.source is source
    assert result.experience.informational_only is True
    assert result.experience.authorizes_execution is False

    deps.repository.record.assert_awaited_once()
    deps.db.commit.assert_awaited_once_with()
    deps.db.refresh.assert_awaited_once_with(record)
    deps.db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_loader_failure_rolls_back_and_skips_repository():
    failure = RuntimeError("canonical source unavailable")

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    loader = SimpleNamespace(load_for_resolution=AsyncMock(side_effect=failure))

    repository = SimpleNamespace(record=AsyncMock())

    service = CustomerSupportObjectiveLearningRecordingService(
        db,
        source_loader=loader,
        repository=repository,
    )

    with pytest.raises(
        RuntimeError,
        match="canonical source unavailable",
    ):
        await service.record_for_resolution(
            user_id=uuid4(),
            resolution_record_id=uuid4(),
        )

    repository.record.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()
    db.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_repository_failure_rolls_back():
    source = _source()

    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    loader = SimpleNamespace(load_for_resolution=AsyncMock(return_value=source))

    repository = SimpleNamespace(
        record=AsyncMock(side_effect=RuntimeError("persistence failed"))
    )

    service = CustomerSupportObjectiveLearningRecordingService(
        db,
        source_loader=loader,
        repository=repository,
    )

    with pytest.raises(
        RuntimeError,
        match="persistence failed",
    ):
        await service.record_for_resolution(
            user_id=uuid4(),
            resolution_record_id=uuid4(),
        )

    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()
    db.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_commit_failure_rolls_back():
    source = _source()

    db = SimpleNamespace(
        commit=AsyncMock(side_effect=RuntimeError("commit failed")),
        rollback=AsyncMock(),
        refresh=AsyncMock(),
    )

    deps = _service(
        source=source,
        db=db,
    )

    with pytest.raises(
        RuntimeError,
        match="commit failed",
    ):
        await deps.service.record_for_resolution(
            user_id=uuid4(),
            resolution_record_id=uuid4(),
        )

    db.refresh.assert_not_awaited()
    db.rollback.assert_awaited_once_with()


def test_service_has_no_event_job_or_planner_activation():
    import ast
    from pathlib import Path

    source = Path(
        "app/domains/customer_service/services/support/learning/"
        "customer_support_objective_learning_recording.py"
    ).read_text(encoding="utf-8")

    tree = ast.parse(source)

    imported_symbols: set[str] = set()
    called_names: set[str] = set()
    assigned_attributes: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_symbols.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported_symbols.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(
                node.func,
                ast.Attribute,
            ):
                called_names.add(node.func.attr)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(
                    target,
                    ast.Attribute,
                ):
                    assigned_attributes.add(target.attr)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(
                node.target,
                ast.Attribute,
            ):
                assigned_attributes.add(node.target.attr)

    forbidden_imports = {
        "PlatformEventPublisher",
        "JobService",
    }

    forbidden_calls = {
        "enqueue",
        "publish",
        "dispatch",
        "rank",
        "rerank",
        "activate",
        "authorize",
    }

    assert not (forbidden_imports & imported_symbols)
    assert not (forbidden_calls & called_names)
    assert "authorizes_execution" not in assigned_attributes

    assert "load_for_resolution" in called_names
    assert "extract_customer_support_objective_learning" in called_names
    assert "record" in called_names
    assert "commit" in called_names
    assert "rollback" in called_names

    assert "commit=False" in source
    assert "await self.db.commit()" in source
    assert "await self.db.rollback()" in source
