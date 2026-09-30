from __future__ import annotations

import pytest

from app.domains.customer_service.services.support.repair.review_plan import (
    CustomerSupportRepairReviewPlanBuilder,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairAction,
    ObjectiveRepairDisposition,
    ObjectiveRepairPlan,
)
from app.runtime.objectives.resolution import (
    ObjectiveReference,
)


def _source_plan() -> SupportReviewPlan:
    return SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        provider_order_id=(
            "gid://shopify/Order/1001"
        ),
        operations=[
            SupportReviewOperation(
                operation_ref="refund-operation",
                operation_type=(
                    SupportReviewOperationType
                    .PARTIAL_REFUND
                ),
                item_id="line-refund",
                item_label="Snowboard",
            ),
            SupportReviewOperation(
                operation_ref=(
                    "replacement-operation"
                ),
                operation_type=(
                    SupportReviewOperationType
                    .REPLACEMENT
                ),
                item_id="line-replacement",
                item_label="Boots",
            ),
            SupportReviewOperation(
                operation_ref="address-operation",
                operation_type=(
                    SupportReviewOperationType
                    .REPLACEMENT_ADDRESS
                ),
                address={
                    "address1": "123 Main Street",
                    "city": "Miami",
                    "province": "FL",
                    "zip": "33101",
                    "country": "US",
                },
            ),
        ],
        approval_required=True,
        execution_allowed=False,
        source_objective_version=3,
    )


def _action(
    *,
    action_ref: str,
    disposition: ObjectiveRepairDisposition,
    operation_ref: str,
) -> ObjectiveRepairAction:
    kwargs = {}

    if (
        disposition
        == ObjectiveRepairDisposition
        .WAIT_FOR_RESULT
    ):
        kwargs["wait_for_event_type"] = (
            "customer_service.support."
            "operation.status_changed"
        )

    return ObjectiveRepairAction(
        action_ref=action_ref,
        disposition=disposition,
        target_operation_refs=(
            operation_ref,
        ),
        reason_code="test_repair",
        summary="Test repair action.",
        confidence=0.9,
        automatic_execution_allowed=False,
        human_approval_required=(
            disposition
            in {
                ObjectiveRepairDisposition
                .REPLAN_REMAINING,
                ObjectiveRepairDisposition
                .REQUEST_HUMAN_ACTION,
            }
        ),
        planner_directives={},
        **kwargs,
    )


def _repair_plan(
    *actions: ObjectiveRepairAction,
) -> ObjectiveRepairPlan:
    target_refs = tuple(
        operation_ref
        for action in actions
        for operation_ref
        in action.target_operation_refs
    )

    return ObjectiveRepairPlan(
        repair_request_ref="repair-request-1",
        objective=ObjectiveReference(
            namespace="customer_service.support",
            objective_type="multi_operation",
            objective_ref="review-1",
            objective_version=1,
        ),
        disposition=actions[0].disposition,
        reason_code="test_plan",
        summary="Test repair plan.",
        confidence=0.9,
        actions=actions,
        planned_target_refs=target_refs,
        deferred_target_refs=(),
        unhandled_target_refs=(),
        automatic_execution_allowed=False,
        human_approval_required=any(
            action.human_approval_required
            for action in actions
        ),
    )


def test_builds_only_replan_remaining_operations():
    repair_plan = _repair_plan(
        _action(
            action_ref="replan-refund",
            disposition=(
                ObjectiveRepairDisposition
                .REPLAN_REMAINING
            ),
            operation_ref="refund-operation",
        ),
        _action(
            action_ref="wait-replacement",
            disposition=(
                ObjectiveRepairDisposition
                .WAIT_FOR_RESULT
            ),
            operation_ref=(
                "replacement-operation"
            ),
        ),
    )

    result = (
        CustomerSupportRepairReviewPlanBuilder()
        .build(
            source_review_plan=_source_plan(),
            repair_plan=repair_plan,
        )
    )

    assert [
        operation.operation_ref
        for operation in result.operations
    ] == [
        "refund-operation",
    ]

    operation = result.operations[0]

    assert operation.operation_type == (
        SupportReviewOperationType
        .PARTIAL_REFUND
    )
    assert operation.item_id == "line-refund"
    assert operation.item_label == "Snowboard"


def test_replacement_preserves_address_scope():
    repair_plan = _repair_plan(
        _action(
            action_ref="replan-replacement",
            disposition=(
                ObjectiveRepairDisposition
                .REPLAN_REMAINING
            ),
            operation_ref=(
                "replacement-operation"
            ),
        ),
    )

    result = (
        CustomerSupportRepairReviewPlanBuilder()
        .build(
            source_review_plan=_source_plan(),
            repair_plan=repair_plan,
        )
    )

    assert [
        operation.operation_ref
        for operation in result.operations
    ] == [
        "replacement-operation",
        "address-operation",
    ]

    address = result.operations[1]

    assert address.address == {
        "address1": "123 Main Street",
        "city": "Miami",
        "province": "FL",
        "zip": "33101",
        "country": "US",
    }


def test_preserves_plan_level_provider_and_order():
    result = (
        CustomerSupportRepairReviewPlanBuilder()
        .build(
            source_review_plan=_source_plan(),
            repair_plan=_repair_plan(
                _action(
                    action_ref="replan-refund",
                    disposition=(
                        ObjectiveRepairDisposition
                        .REPLAN_REMAINING
                    ),
                    operation_ref=(
                        "refund-operation"
                    ),
                )
            ),
        )
    )

    assert result.order_ref == "#1001"
    assert result.provider == "shopify"
    assert result.provider_order_id == (
        "gid://shopify/Order/1001"
    )
    assert result.source_objective_version == 3


def test_result_remains_approval_blocked():
    source = _source_plan()

    source.operations[0].approval_required = False
    source.operations[0].execution_allowed = True

    result = (
        CustomerSupportRepairReviewPlanBuilder()
        .build(
            source_review_plan=source,
            repair_plan=_repair_plan(
                _action(
                    action_ref="replan-refund",
                    disposition=(
                        ObjectiveRepairDisposition
                        .REPLAN_REMAINING
                    ),
                    operation_ref=(
                        "refund-operation"
                    ),
                )
            ),
        )
    )

    assert result.approval_required is True
    assert result.execution_allowed is False
    assert all(
        operation.approval_required is True
        for operation in result.operations
    )
    assert all(
        operation.execution_allowed is False
        for operation in result.operations
    )


def test_source_plan_is_not_mutated():
    source = _source_plan()

    result = (
        CustomerSupportRepairReviewPlanBuilder()
        .build(
            source_review_plan=source,
            repair_plan=_repair_plan(
                _action(
                    action_ref="replan-replacement",
                    disposition=(
                        ObjectiveRepairDisposition
                        .REPLAN_REMAINING
                    ),
                    operation_ref=(
                        "replacement-operation"
                    ),
                )
            ),
        )
    )

    result.operations[1].address["city"] = (
        "Changed"
    )

    assert (
        source.operations[2].address["city"]
        == "Miami"
    )


def test_unknown_operation_ref_is_rejected():
    with pytest.raises(
        ValueError,
        match="not found in source review plan",
    ):
        (
            CustomerSupportRepairReviewPlanBuilder()
            .build(
                source_review_plan=_source_plan(),
                repair_plan=_repair_plan(
                    _action(
                        action_ref="replan-missing",
                        disposition=(
                            ObjectiveRepairDisposition
                            .REPLAN_REMAINING
                        ),
                        operation_ref=(
                            "missing-operation"
                        ),
                    )
                ),
            )
        )


def test_address_cannot_be_replanned_alone():
    with pytest.raises(
        ValueError,
        match=(
            "Replacement address cannot be "
            "replanned"
        ),
    ):
        (
            CustomerSupportRepairReviewPlanBuilder()
            .build(
                source_review_plan=_source_plan(),
                repair_plan=_repair_plan(
                    _action(
                        action_ref="replan-address",
                        disposition=(
                            ObjectiveRepairDisposition
                            .REPLAN_REMAINING
                        ),
                        operation_ref=(
                            "address-operation"
                        ),
                    )
                ),
            )
        )


def test_plan_without_replan_actions_is_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "contains no REPLAN_REMAINING"
        ),
    ):
        (
            CustomerSupportRepairReviewPlanBuilder()
            .build(
                source_review_plan=_source_plan(),
                repair_plan=_repair_plan(
                    _action(
                        action_ref="wait-refund",
                        disposition=(
                            ObjectiveRepairDisposition
                            .WAIT_FOR_RESULT
                        ),
                        operation_ref=(
                            "refund-operation"
                        ),
                    )
                ),
            )
        )


def test_duplicate_replan_target_is_rejected_by_contract():
    with pytest.raises(
        ValueError,
        match="planned target refs must be unique",
    ):
        _repair_plan(
            _action(
                action_ref="replan-first",
                disposition=(
                    ObjectiveRepairDisposition
                    .REPLAN_REMAINING
                ),
                operation_ref="refund-operation",
            ),
            _action(
                action_ref="replan-second",
                disposition=(
                    ObjectiveRepairDisposition
                    .REPLAN_REMAINING
                ),
                operation_ref="refund-operation",
            ),
        )


def test_source_operations_require_stable_refs():
    source = _source_plan()
    source.operations[0].operation_ref = None

    with pytest.raises(
        ValueError,
        match="must have an operation_ref",
    ):
        (
            CustomerSupportRepairReviewPlanBuilder()
            .build(
                source_review_plan=source,
                repair_plan=_repair_plan(
                    _action(
                        action_ref="replan-refund",
                        disposition=(
                            ObjectiveRepairDisposition
                            .REPLAN_REMAINING
                        ),
                        operation_ref=(
                            "refund-operation"
                        ),
                    )
                ),
            )
        )
