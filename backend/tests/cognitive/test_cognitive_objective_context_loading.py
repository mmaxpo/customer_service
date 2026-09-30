from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.tcos import (
    ExecuteGoalRuntimeRequest,
)
from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
    ObjectiveCognitiveIdentity,
    ObjectiveCognitiveProvenance,
    ObjectiveCognitiveReference,
)
from app.tcos.cognitive import CognitiveRuntime
from app.tcos.execution import ExecutionStatus


class FakeAdapter:
    async def execute(
        self,
        *,
        workflow,
        message,
        ctx,
        strict=True,
    ):
        return {
            "answer": "ok",
            "meta": {
                "status": "ok",
            },
        }


def _absent_context():
    return ObjectiveCognitiveContext(
        present=False,
        identity=ObjectiveCognitiveIdentity(
            namespace="customer_service.support",
            objective_ref="review-plan-1",
        ),
        provenance=ObjectiveCognitiveProvenance(),
    )


def _patch_runtime_execution(monkeypatch):
    from app.tcos.execution.coordinator import (
        ExecutionCoordinator,
    )

    original_execute = ExecutionCoordinator.execute

    async def fake_execute(
        self,
        execution_graph,
        *,
        ctx,
        message,
        strict=True,
        backend=None,
        adapter=None,
    ):
        return await original_execute(
            self,
            execution_graph,
            ctx=ctx,
            message=message,
            strict=strict,
            adapter=FakeAdapter(),
        )

    monkeypatch.setattr(
        ExecutionCoordinator,
        "execute",
        fake_execute,
    )


@pytest.mark.asyncio
async def test_runtime_loads_explicit_objective_context(
    monkeypatch,
):
    from app.runtime.objectives.cognition import (
        ObjectiveCognitiveContextLoader,
    )

    load = AsyncMock(return_value=_absent_context())

    monkeypatch.setattr(
        ObjectiveCognitiveContextLoader,
        "load_for_objective",
        load,
    )
    _patch_runtime_execution(monkeypatch)

    user_id = uuid4()
    db = object()

    session = await CognitiveRuntime().execute_goal_runtime(
        goal="Summarize https://example.com",
        ctx=SimpleNamespace(
            db=db,
            user_id=user_id,
            tenant_id="tenant-1",
        ),
        user_id=str(user_id),
        objective=(
            ObjectiveCognitiveReference(
                namespace=("customer_service.support"),
                objective_ref="review-plan-1",
            )
        ),
    )

    load.assert_awaited_once_with(
        user_id=str(user_id),
        objective_namespace=("customer_service.support"),
        objective_ref="review-plan-1",
        tenant_id="tenant-1",
    )

    planner_context = session.planner_session["context"]

    assert planner_context["objective_context"]["present"] is False

    assert session.execution_session["status"] == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_runtime_uses_context_user_when_argument_missing(
    monkeypatch,
):
    from app.runtime.objectives.cognition import (
        ObjectiveCognitiveContextLoader,
    )

    load = AsyncMock(return_value=_absent_context())

    monkeypatch.setattr(
        ObjectiveCognitiveContextLoader,
        "load_for_objective",
        load,
    )
    _patch_runtime_execution(monkeypatch)

    user_id = uuid4()

    await CognitiveRuntime().execute_goal_runtime(
        goal="Summarize https://example.com",
        ctx=SimpleNamespace(
            db=object(),
            user_id=user_id,
        ),
        objective=ObjectiveCognitiveReference(
            namespace="customer_service.support",
            objective_ref="review-plan-1",
        ),
    )

    load.assert_awaited_once_with(
        user_id=user_id,
        objective_namespace=("customer_service.support"),
        objective_ref="review-plan-1",
        tenant_id=None,
    )


@pytest.mark.asyncio
async def test_runtime_does_not_query_without_reference(
    monkeypatch,
):
    from app.runtime.objectives.cognition import (
        ObjectiveCognitiveContextLoader,
    )

    load = AsyncMock()

    monkeypatch.setattr(
        ObjectiveCognitiveContextLoader,
        "load_for_objective",
        load,
    )
    _patch_runtime_execution(monkeypatch)

    session = await CognitiveRuntime().execute_goal_runtime(
        goal="Summarize https://example.com",
        ctx=object(),
    )

    load.assert_not_awaited()

    assert session.planner_session["context"]["objective_context"] is None


@pytest.mark.asyncio
async def test_explicit_reference_requires_database():
    with pytest.raises(
        ValueError,
        match="runtime database session",
    ):
        await CognitiveRuntime().execute_goal_runtime(
            goal="Reply to customer",
            ctx=SimpleNamespace(user_id=uuid4()),
            objective=(
                ObjectiveCognitiveReference(
                    namespace=("customer_service.support"),
                    objective_ref=("review-plan-1"),
                )
            ),
        )


@pytest.mark.asyncio
async def test_explicit_reference_requires_user_id():
    with pytest.raises(
        ValueError,
        match="authenticated user id",
    ):
        await CognitiveRuntime().execute_goal_runtime(
            goal="Reply to customer",
            ctx=SimpleNamespace(db=object()),
            objective=(
                ObjectiveCognitiveReference(
                    namespace=("customer_service.support"),
                    objective_ref=("review-plan-1"),
                )
            ),
        )


def test_runtime_request_accepts_objective_reference():
    request = ExecuteGoalRuntimeRequest(
        goal="Reply to customer",
        objective={
            "namespace": ("customer_service.support"),
            "objective_ref": "review-plan-1",
        },
    )

    assert request.objective == (
        ObjectiveCognitiveReference(
            namespace=("customer_service.support"),
            objective_ref="review-plan-1",
        )
    )


def test_runtime_request_remains_backward_compatible():
    request = ExecuteGoalRuntimeRequest(goal="Reply to customer")

    assert request.objective is None
    assert request.strict is True
    assert request.thread_id is None


def test_runtime_request_rejects_partial_reference():
    with pytest.raises(ValidationError):
        ExecuteGoalRuntimeRequest(
            goal="Reply to customer",
            objective={
                "namespace": ("customer_service.support"),
            },
        )


def test_runtime_request_rejects_extra_objective_fields():
    with pytest.raises(ValidationError):
        ExecuteGoalRuntimeRequest(
            goal="Reply to customer",
            objective={
                "namespace": ("customer_service.support"),
                "objective_ref": ("review-plan-1"),
                "infer_from_goal": True,
            },
        )


def test_synchronous_cognitive_runtime_accepts_transport_only():
    context = _absent_context()

    from app.tcos.planner.runtime.planning_inputs import (
        build_default_planning_context,
    )

    session = CognitiveRuntime().execute_goal(
        goal="Summarize https://example.com",
        planning_context=(
            build_default_planning_context(
                user_message="Summarize https://example.com",
                objective_context=context,
            )
        ),
    )

    assert session.status.value == "completed"
    assert session.planner_session["context"]["objective_context"]["present"] is False


def test_synchronous_cognitive_runtime_remains_database_free():
    session = CognitiveRuntime().execute_goal(goal="Summarize https://example.com")

    assert session.status.value == "completed"
    assert session.planner_session["context"]["objective_context"] is None


def test_reference_contract_is_immutable():
    reference = ObjectiveCognitiveReference(
        namespace="test.objective",
        objective_ref="objective-1",
    )

    with pytest.raises(ValidationError):
        reference.namespace = "changed"
