from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domains.customer_service.services.support.learning.customer_support_objective_learning_source_loader import (
    CustomerSupportObjectiveLearningSourceLineageError,
    CustomerSupportObjectiveLearningSourceLoader,
    CustomerSupportObjectiveLearningSourceNotFoundError,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewPlan,
)


NOW = datetime(
    2026,
    8,
    3,
    12,
    0,
    tzinfo=timezone.utc,
)


def _resolution(
    *,
    user_id,
    record_id,
    outcome_id,
    evaluation_id,
    tenant_id="tenant-1",
):
    return SimpleNamespace(
        id=record_id,
        user_id=user_id,
        tenant_id=tenant_id,
        objective_namespace=("customer_service.support"),
        objective_type="multi_operation",
        objective_ref="review-plan-1",
        objective_version=1,
        source_outcome_ref=str(outcome_id),
        outcome_version=1,
        source_evaluation_ref=(str(evaluation_id)),
        evaluation_version=1,
        projection_version=1,
        assessment_schema_version=("objective_resolution_assessment.v1"),
        workflow_run_id="workflow-run-1",
        assessment_json={
            "objective": {
                "namespace": ("customer_service.support"),
                "objective_type": ("multi_operation"),
                "objective_ref": ("review-plan-1"),
                "objective_version": 1,
            },
            "status": "partially_achieved",
            "operations": [
                {
                    "operation_ref": "lookup",
                    "operation_type": ("order_lookup"),
                    "status": "achieved",
                    "required": True,
                    "verification_ref": ("verify:lookup"),
                },
                {
                    "operation_ref": "refund",
                    "operation_type": ("order_action"),
                    "status": "failed",
                    "reason_code": ("provider_rejected"),
                    "required": True,
                    "verification_ref": ("verify:refund"),
                },
            ],
            "evidence_refs": [
                "verify:lookup",
                "verify:refund",
            ],
        },
    )


def _review_plan(
    *,
    resolution_record_id,
    outcome_id,
    workflow_run_id,
):
    return SimpleNamespace(
        review_plan_id="review-plan-1",
        review_plan=SupportReviewPlan(
            order_ref="order-1",
            provider="shopify",
            operations=[
                {
                    "sequence": 1,
                    "operation_ref": "lookup",
                    "operation_type": ("whole_refund"),
                    "required": True,
                    "capability_id": ("ecommerce.orders.get"),
                    "provider_id": "shopify",
                    "provider_ref": ("shopify.order_read"),
                },
                {
                    "sequence": 2,
                    "operation_ref": "refund",
                    "operation_type": ("partial_refund"),
                    "required": True,
                    "capability_id": ("ecommerce.orders.manage"),
                    "provider_id": "shopify",
                    "provider_ref": ("shopify.order_action"),
                },
            ],
        ),
        support_outcome_id=outcome_id,
        workflow_run_id=workflow_run_id,
        resolution_record_id=(resolution_record_id),
    )


def _outcome(
    *,
    user_id,
    outcome_id,
    workflow_run_id,
):
    return SimpleNamespace(
        id=outcome_id,
        user_id=user_id,
        review_plan_id="review-plan-1",
        workflow_run_id=workflow_run_id,
        objective_namespace=("customer_service.support"),
        objective_type="multi_operation",
        objective_ref="review-plan-1",
        source_objective_version=1,
        outcome_version=1,
        outcome_json={
            "objective_namespace": ("customer_service.support"),
            "objective_type": ("multi_operation"),
            "objective_ref": ("review-plan-1"),
            "objective_version": 1,
            "result": "partially_achieved",
        },
    )


def _evaluation(
    *,
    user_id,
    evaluation_id,
    outcome_id,
    workflow_run_id,
):
    return SimpleNamespace(
        id=evaluation_id,
        user_id=user_id,
        support_outcome_id=outcome_id,
        review_plan_id="review-plan-1",
        workflow_run_id=workflow_run_id,
        evaluation_version=1,
        result="partially_achieved",
        reason_code=("one_or_more_operations_failed"),
        summary="Refund failed.",
        confidence=0.96,
        retryable=True,
        achieved_operation_count=1,
        failed_operation_count=1,
        pending_operation_count=0,
        unknown_operation_count=0,
        not_executed_operation_count=0,
        observed_outcome_json={
            "result": "partially_achieved",
        },
        evidence_json=[
            {
                "evidence_ref": ("provider-state:refund"),
                "source_type": ("provider_confirmation"),
            }
        ],
    )


def _repair(
    *,
    user_id,
    resolution_record_id,
    attempt_number=1,
    tenant_id="tenant-1",
):
    return SimpleNamespace(
        id=uuid4(),
        source_event_id=uuid4(),
        user_id=user_id,
        tenant_id=tenant_id,
        resolution_record_id=(resolution_record_id),
        objective_namespace=("customer_service.support"),
        objective_type="multi_operation",
        objective_ref="review-plan-1",
        objective_version=1,
        repair_request_ref=(f"repair-request-{attempt_number}"),
        repair_request_version=1,
        repair_plan_version=1,
        planner_ref=("customer_support.repair_planner"),
        planner_policy_version=1,
        controlling_disposition=("replan_remaining"),
        status="succeeded",
        attempt_number=attempt_number,
        requires_human_approval=True,
        automatic_execution_allowed=False,
        request_json={
            "repair_request_ref": (f"repair-request-{attempt_number}"),
        },
        plan_json={
            "disposition": ("replan_remaining"),
            "actions": [
                {
                    "action_ref": (f"action-{attempt_number}"),
                    "target_operation_refs": ["refund"],
                }
            ],
        },
        workflow_json=None,
        workflow_job_id=None,
        workflow_run_id=None,
        result_json={"status": "succeeded"},
        failure_code=None,
        failure_message=None,
        created_at=NOW,
        launched_at=NOW,
        completed_at=NOW,
    )


def _loader(
    *,
    resolution,
    plan,
    outcome,
    evaluation,
    repairs=(),
):
    return SimpleNamespace(
        loader=(
            CustomerSupportObjectiveLearningSourceLoader(
                SimpleNamespace(),
                resolutions=SimpleNamespace(
                    get_for_user=AsyncMock(return_value=resolution)
                ),
                review_plans=SimpleNamespace(
                    load_for_resolution=AsyncMock(return_value=plan)
                ),
                outcomes=SimpleNamespace(get_for_user=AsyncMock(return_value=outcome)),
                evaluations=SimpleNamespace(
                    get_by_outcome_version=(AsyncMock(return_value=evaluation))
                ),
                repairs=SimpleNamespace(
                    list_for_resolution=AsyncMock(return_value=list(repairs))
                ),
            )
        )
    )


@pytest.mark.asyncio
async def test_loader_assembles_canonical_source():
    user_id = uuid4()
    resolution_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()
    workflow_run_id = uuid4()

    resolution = _resolution(
        user_id=user_id,
        record_id=resolution_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
    )

    repairs = (
        _repair(
            user_id=user_id,
            resolution_record_id=(resolution_id),
            attempt_number=1,
        ),
        _repair(
            user_id=user_id,
            resolution_record_id=(resolution_id),
            attempt_number=2,
        ),
    )

    deps = _loader(
        resolution=resolution,
        plan=_review_plan(
            resolution_record_id=resolution_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        outcome=_outcome(
            user_id=user_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        evaluation=_evaluation(
            user_id=user_id,
            evaluation_id=evaluation_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        repairs=repairs,
    )

    source = await deps.loader.load_for_resolution(
        user_id=user_id,
        resolution_record_id=resolution_id,
        tenant_id="tenant-1",
    )

    assert source.user_id == str(user_id)
    assert source.tenant_id == "tenant-1"
    assert source.resolution_record_id == (str(resolution_id))
    assert source.outcome_ref == str(outcome_id)
    assert source.evaluation_ref == (str(evaluation_id))
    assert source.review_plan_id == ("review-plan-1")
    assert source.workflow_run_id == (str(workflow_run_id))

    # The canonical support review plan retains its top-level
    # provider, but the current operation contract does not retain
    # capability IDs or provider executor references. The loader
    # must not infer or fabricate those identities.
    assert source.capability_ids == ()
    assert source.provider_ids == ("shopify",)
    assert source.provider_refs == ()

    assert tuple(item["attempt_number"] for item in source.repair_executions) == (1, 2)

    assert source.evidence_refs == (
        "verify:lookup",
        "verify:refund",
        "provider-state:refund",
    )

    assert source.metadata["read_only"] is True
    assert source.metadata["repair_execution_count"] == 2

    dumped = source.model_dump(mode="json")
    assert dumped == (source.model_validate(dumped).model_dump(mode="json"))


@pytest.mark.asyncio
async def test_loader_uses_exact_repository_reads():
    user_id = uuid4()
    resolution_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()
    workflow_run_id = uuid4()

    resolution = _resolution(
        user_id=user_id,
        record_id=resolution_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
    )

    deps = _loader(
        resolution=resolution,
        plan=_review_plan(
            resolution_record_id=resolution_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        outcome=_outcome(
            user_id=user_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        evaluation=_evaluation(
            user_id=user_id,
            evaluation_id=evaluation_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
    )

    await deps.loader.load_for_resolution(
        user_id=user_id,
        resolution_record_id=resolution_id,
        repair_limit=37,
    )

    (
        deps.loader.resolutions.get_for_user.assert_awaited_once_with(
            user_id=user_id,
            record_id=resolution_id,
        )
    )
    (
        deps.loader.review_plans.load_for_resolution.assert_awaited_once_with(
            user_id=user_id,
            resolution_record_id=(resolution_id),
        )
    )
    (
        deps.loader.outcomes.get_for_user.assert_awaited_once_with(
            user_id=user_id,
            outcome_id=outcome_id,
        )
    )
    (
        deps.loader.evaluations.get_by_outcome_version.assert_awaited_once_with(
            user_id=user_id,
            support_outcome_id=outcome_id,
            evaluation_version=1,
        )
    )
    (
        deps.loader.repairs.list_for_resolution.assert_awaited_once_with(
            user_id=user_id,
            resolution_record_id=(resolution_id),
            limit=37,
        )
    )


@pytest.mark.asyncio
async def test_missing_resolution_is_not_found():
    loader = CustomerSupportObjectiveLearningSourceLoader(
        SimpleNamespace(),
        resolutions=SimpleNamespace(get_for_user=AsyncMock(return_value=None)),
        review_plans=SimpleNamespace(),
        outcomes=SimpleNamespace(),
        evaluations=SimpleNamespace(),
        repairs=SimpleNamespace(),
    )

    with pytest.raises(
        CustomerSupportObjectiveLearningSourceNotFoundError,
        match="resolution record",
    ):
        await loader.load_for_resolution(
            user_id=uuid4(),
            resolution_record_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_requested_tenant_is_enforced():
    user_id = uuid4()
    resolution_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()

    resolution = _resolution(
        user_id=user_id,
        record_id=resolution_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
        tenant_id="tenant-other",
    )

    review_plans = SimpleNamespace(load_for_resolution=AsyncMock())

    loader = CustomerSupportObjectiveLearningSourceLoader(
        SimpleNamespace(),
        resolutions=SimpleNamespace(get_for_user=AsyncMock(return_value=resolution)),
        review_plans=review_plans,
        outcomes=SimpleNamespace(),
        evaluations=SimpleNamespace(),
        repairs=SimpleNamespace(),
    )

    with pytest.raises(
        CustomerSupportObjectiveLearningSourceNotFoundError,
        match="tenant",
    ):
        await loader.load_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_id,
            tenant_id="tenant-1",
        )

    (review_plans.load_for_resolution.assert_not_awaited())


@pytest.mark.asyncio
async def test_evaluation_identity_mismatch_is_rejected():
    user_id = uuid4()
    resolution_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()
    workflow_run_id = uuid4()

    resolution = _resolution(
        user_id=user_id,
        record_id=resolution_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
    )

    evaluation = _evaluation(
        user_id=user_id,
        evaluation_id=uuid4(),
        outcome_id=outcome_id,
        workflow_run_id=workflow_run_id,
    )

    deps = _loader(
        resolution=resolution,
        plan=_review_plan(
            resolution_record_id=resolution_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        outcome=_outcome(
            user_id=user_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        evaluation=evaluation,
    )

    with pytest.raises(
        CustomerSupportObjectiveLearningSourceLineageError,
        match="source evaluation",
    ):
        await deps.loader.load_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_id,
        )


@pytest.mark.asyncio
async def test_repair_lineage_mismatch_is_rejected():
    user_id = uuid4()
    resolution_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()
    workflow_run_id = uuid4()

    resolution = _resolution(
        user_id=user_id,
        record_id=resolution_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
    )

    repair = _repair(
        user_id=user_id,
        resolution_record_id=uuid4(),
    )

    deps = _loader(
        resolution=resolution,
        plan=_review_plan(
            resolution_record_id=resolution_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        outcome=_outcome(
            user_id=user_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        evaluation=_evaluation(
            user_id=user_id,
            evaluation_id=evaluation_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        repairs=(repair,),
    )

    with pytest.raises(
        CustomerSupportObjectiveLearningSourceLineageError,
        match="requested resolution",
    ):
        await deps.loader.load_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_id,
        )


@pytest.mark.asyncio
async def test_loader_allows_empty_repair_history():
    user_id = uuid4()
    resolution_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()
    workflow_run_id = uuid4()

    resolution = _resolution(
        user_id=user_id,
        record_id=resolution_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
    )

    deps = _loader(
        resolution=resolution,
        plan=_review_plan(
            resolution_record_id=resolution_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        outcome=_outcome(
            user_id=user_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        evaluation=_evaluation(
            user_id=user_id,
            evaluation_id=evaluation_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
    )

    source = await deps.loader.load_for_resolution(
        user_id=user_id,
        resolution_record_id=resolution_id,
    )

    assert source.repair_executions == ()


def test_loader_source_contains_no_write_boundary():
    source = (
        __import__("pathlib")
        .Path(
            "app/domains/customer_service/services/support/learning/"
            "customer_support_objective_learning_source_loader.py"
        )
        .read_text(encoding="utf-8")
    )

    for forbidden in (
        ".commit(",
        ".flush(",
        ".add(",
        ".publish(",
        ".enqueue(",
        ".record(",
        ".extract(",
    ):
        assert forbidden not in source


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "field_name",
        "outcome_value",
        "message",
    ),
    (
        (
            "objective_namespace",
            "other.namespace",
            "objective_namespace",
        ),
        (
            "objective_type",
            "other_type",
            "objective_type",
        ),
        (
            "objective_ref",
            "other-review-plan",
            "objective_ref",
        ),
        (
            "source_objective_version",
            2,
            "objective_version",
        ),
    ),
)
async def test_outcome_objective_lineage_mismatch_is_rejected(
    field_name,
    outcome_value,
    message,
):
    user_id = uuid4()
    resolution_id = uuid4()
    outcome_id = uuid4()
    evaluation_id = uuid4()
    workflow_run_id = uuid4()

    resolution = _resolution(
        user_id=user_id,
        record_id=resolution_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
    )

    outcome = _outcome(
        user_id=user_id,
        outcome_id=outcome_id,
        workflow_run_id=workflow_run_id,
    )

    setattr(
        outcome,
        field_name,
        outcome_value,
    )

    deps = _loader(
        resolution=resolution,
        plan=_review_plan(
            resolution_record_id=resolution_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
        outcome=outcome,
        evaluation=_evaluation(
            user_id=user_id,
            evaluation_id=evaluation_id,
            outcome_id=outcome_id,
            workflow_run_id=workflow_run_id,
        ),
    )

    with pytest.raises(
        CustomerSupportObjectiveLearningSourceLineageError,
        match=message,
    ):
        await deps.loader.load_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_id,
        )


def test_objective_lineage_uses_source_objective_version():
    source = (
        __import__("pathlib")
        .Path(
            "app/domains/customer_service/services/support/learning/"
            "customer_support_objective_learning_source_loader.py"
        )
        .read_text(encoding="utf-8")
    )

    assert "outcome.source_objective_version" in source
    assert "resolution.objective_version" in source


def test_canonical_review_plan_does_not_retain_undeclared_scope_fields():
    loaded = _review_plan(
        resolution_record_id=uuid4(),
        outcome_id=uuid4(),
        workflow_run_id=uuid4(),
    )

    dumped = loaded.review_plan.model_dump(mode="json")

    assert dumped["provider"] == "shopify"
    assert len(dumped["operations"]) == 2

    for operation in dumped["operations"]:
        assert "capability_id" not in operation
        assert "provider_id" not in operation
        assert "provider_ref" not in operation


def test_provider_scope_never_infers_capabilities_or_refs():
    capability_ids, provider_ids, provider_refs = (
        CustomerSupportObjectiveLearningSourceLoader._provider_scope(
            {
                "provider": "Shopify",
                "operations": [
                    {
                        "operation_ref": "refund",
                        "operation_type": ("partial_refund"),
                    }
                ],
            }
        )
    )

    assert capability_ids == ()
    assert provider_ids == ("shopify",)
    assert provider_refs == ()
