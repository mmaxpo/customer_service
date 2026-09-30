from app.domains.customer_service.services.shopify_workflow_catalog import (
    shopify_system_workflow_templates,
)


def _refund_template():
    return next(
        template
        for template in shopify_system_workflow_templates()
        if template["name"] == "Shopify Refund Request Workflow"
    )


def test_refund_workflow_persists_chat_session_before_approval():
    workflow = _refund_template()["workflow_json"]

    nodes = {
        node["id"]: node["data"]
        for node in workflow["nodes"]
    }

    assert nodes["capture_customer_chat_session"] == {
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
        "target": "extract_order_ref",
    } in workflow["edges"]


def test_refund_rejection_is_delivered_to_customer_chat():
    workflow = _refund_template()["workflow_json"]

    nodes = {
        node["id"]: node["data"]
        for node in workflow["nodes"]
    }

    assert nodes["reply_rejection_to_customer"] == {
        "nodeType": "reply.customer_chat",
        "session_id_from": "vars",
        "session_id_key": "customer_chat_session_id",
        "message_from": "vars",
        "message_key": "final_message",
        "save_as": "customer_chat_delivery",
    }

    assert {
        "source": "set_rejected_message",
        "target": "reply_rejection_to_customer",
    } in workflow["edges"]

    assert {
        "source": "reply_rejection_to_customer",
        "target": "rejected_response",
    } in workflow["edges"]


def test_refund_missing_order_does_not_create_second_chat_reply():
    workflow = _refund_template()["workflow_json"]

    outgoing = [
        edge
        for edge in workflow["edges"]
        if edge["source"] == "set_missing_order_message"
    ]

    assert outgoing == [
        {
            "source": "set_missing_order_message",
            "target": "missing_order_response",
        }
    ]
