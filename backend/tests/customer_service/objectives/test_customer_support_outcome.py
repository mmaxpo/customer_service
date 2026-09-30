from app.domains.customer_service.services.support.outcome.customer_support_outcome import (
    CustomerSupportOutcomeProjector,
    SupportOutcomeStatus,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)


def _review_plan(
    operation_type: SupportReviewOperationType,
) -> SupportReviewPlan:
    return SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        provider_order_id="6972738601127",
        operations=[
            SupportReviewOperation(
                operation_type=operation_type,
            )
        ],
    )


def test_projects_prepared_refund_without_overclaiming():
    plan = _review_plan(
        SupportReviewOperationType.WHOLE_REFUND
    )

    outcome = CustomerSupportOutcomeProjector().project(
        review_plan_id="review-1",
        support_review={
            "review_plan_id": "review-1",
            "review_plan": plan.model_dump(mode="json"),
        },
        approval_result=True,
        prepared_operations={
            "prepare_whole_refund": {
                "action": "refund",
                "status": "prepared",
                "order_name": "#1001",
            }
        },
    )

    assert outcome.decision == "approved"
    assert len(outcome.operations) == 1

    operation = outcome.operations[0]

    assert operation.status == SupportOutcomeStatus.PREPARED
    assert operation.prepared is True
    assert operation.submitted is False
    assert operation.completed is False

    assert outcome.customer_message == (
        "Your refund request for order #1001 was approved. "
        "The refund has been prepared, but it has not been "
        "submitted yet."
    )


def test_projects_rejected_refund_without_claiming_action():
    plan = _review_plan(
        SupportReviewOperationType.WHOLE_REFUND
    )

    outcome = CustomerSupportOutcomeProjector().project(
        review_plan_id="review-1",
        support_review={
            "review_plan_id": "review-1",
            "review_plan": plan.model_dump(mode="json"),
        },
        approval_result=False,
    )

    assert outcome.decision == "rejected"
    assert outcome.operations[0].status == (
        SupportOutcomeStatus.REJECTED
    )
    assert outcome.customer_message == (
        "Your refund request for order #1001 was not approved. "
        "No refund was submitted."
    )


def test_projects_completed_refund_only_when_result_says_completed():
    plan = _review_plan(
        SupportReviewOperationType.WHOLE_REFUND
    )

    outcome = CustomerSupportOutcomeProjector().project(
        review_plan_id="review-1",
        support_review={
            "review_plan_id": "review-1",
            "review_plan": plan.model_dump(mode="json"),
        },
        approval_result=True,
        prepared_operations={
            "prepare_whole_refund": {
                "action": "refund",
                "status": "completed",
            }
        },
    )

    operation = outcome.operations[0]

    assert operation.completed is True
    assert operation.submitted is True
    assert outcome.customer_message == (
        "Your refund for order #1001 has been completed."
    )
