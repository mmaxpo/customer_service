from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.domains.customer_service.services.support.planning.customer_support_review_workflow import (
    CustomerSupportReviewWorkflowBuilder,
)


def _node(workflow: dict, node_id: str) -> dict:
    return next(
        node
        for node in workflow["nodes"]
        if node["id"] == node_id
    )


def test_review_workflow_delivers_approved_outcome_to_customer_chat():
    plan = SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        provider_order_id="6972738601127",
        operations=[
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.WHOLE_REFUND
                )
            )
        ],
    )

    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-1",
        review_plan=plan,
    )

    projection = _node(
        workflow,
        "project_approved_outcome",
    )
    reply = _node(
        workflow,
        "reply_approved_outcome",
    )

    assert projection["data"]["nodeType"] == (
        "customer_service.project_support_outcome"
    )

    assert reply["data"] == {
        "nodeType": "reply.customer_chat",
        "session_id_from": "vars",
        "session_id_key": "customer_chat_session_id",
        "message_from": "vars",
        "message_key": "customer_message",
        "save_as": "customer_outcome_delivery",
    }

    assert {
        "source": "join_preparation_results",
        "target": "project_approved_outcome",
    } in workflow["edges"]

    record = _node(workflow, "record_approved_outcome")
    assert record["data"]["nodeType"] == (
        "customer_service.record_support_outcome"
    )

    assert {
        "source": "project_approved_outcome",
        "target": "record_approved_outcome",
    } in workflow["edges"]

    assert {
        "source": "record_approved_outcome",
        "target": "reply_approved_outcome",
    } in workflow["edges"]

    assert {
        "source": "reply_approved_outcome",
        "target": "approved_response",
    } in workflow["edges"]


def test_review_workflow_delivers_rejection_to_customer_chat():
    plan = SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        operations=[
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.WHOLE_REFUND
                )
            )
        ],
    )

    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-1",
        review_plan=plan,
    )

    assert {
        "source": "set_rejected_result",
        "target": "project_rejected_outcome",
    } in workflow["edges"]

    record = _node(workflow, "record_rejected_outcome")
    assert record["data"]["nodeType"] == (
        "customer_service.record_support_outcome"
    )

    assert {
        "source": "project_rejected_outcome",
        "target": "record_rejected_outcome",
    } in workflow["edges"]

    assert {
        "source": "record_rejected_outcome",
        "target": "reply_rejected_outcome",
    } in workflow["edges"]

    assert {
        "source": "reply_rejected_outcome",
        "target": "rejected_response",
    } in workflow["edges"]


def test_review_workflow_persists_customer_chat_session_before_approval():
    plan = SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        operations=[
            SupportReviewOperation(
                operation_type=(
                    SupportReviewOperationType.WHOLE_REFUND
                )
            )
        ],
    )

    workflow = CustomerSupportReviewWorkflowBuilder().build(
        review_plan_id="review-1",
        review_plan=plan,
    )

    capture = _node(
        workflow,
        "capture_customer_chat_session",
    )

    assert capture["data"] == {
        "nodeType": "context.extract",
        "source": "event_payload",
        "path": "session_id",
        "save_as": "customer_chat_session_id",
        "required": True,
    }

    assert {
        "source": "trigger",
        "target": "capture_customer_chat_session",
    } in workflow["edges"]

    assert {
        "source": "capture_customer_chat_session",
        "target": "extract_support_review",
    } in workflow["edges"]

    for node_id in (
        "reply_approved_outcome",
        "reply_rejected_outcome",
    ):
        reply = _node(workflow, node_id)

        assert (
            reply["data"]["session_id_from"]
            == "vars"
        )
        assert (
            reply["data"]["session_id_key"]
            == "customer_chat_session_id"
        )
