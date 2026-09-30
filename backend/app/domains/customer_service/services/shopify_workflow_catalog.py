from __future__ import annotations


def shopify_system_workflow_templates() -> list[dict]:
    return [
        _template(
            name="Shopify Refund Request Workflow",
            description="Looks up Shopify order context, prepares a refund action, pauses for human approval, then drafts a customer response.",
            tags=["shopify", "refund", "support", "human_approval"],
            action="refund",
            intent="refund_request",
            requires_approval=True,
            response_message="Refund workflow completed after Shopify order lookup and approval.",
        ),
        _template(
            name="Shopify Order Cancellation Workflow",
            description="Looks up order state, prepares cancellation, and requires approval before risky order action execution.",
            tags=["shopify", "cancel", "support", "escalation"],
            action="cancel",
            intent="cancellation",
            requires_approval=True,
            response_message="Cancellation workflow prepared and routed through approval.",
        ),
        _template(
            name="Shopify Shipping Status Workflow",
            description="Looks up Shopify order context and prepares shipping status response without manual approval.",
            tags=["shopify", "shipping", "tracking", "support"],
            action="shipping_status",
            intent="shipping_delay",
            requires_approval=False,
            response_message="Shipping status workflow completed with Shopify order context.",
        ),
        _template(
            name="Shopify Damaged Item Workflow",
            description="Looks up order context, prepares damaged-item support action, and pauses for review.",
            tags=["shopify", "damaged_item", "support", "escalation"],
            action="damaged_item",
            intent="damaged_item",
            requires_approval=True,
            response_message="Damaged item workflow prepared for support review.",
        ),
    ]


def _template(
    *,
    name: str,
    description: str,
    tags: list[str],
    action: str,
    intent: str,
    requires_approval: bool,
    response_message: str,
) -> dict:
    nodes = [
        {
            "id": "trigger",
            "type": "trigger",
            "data": {
                "nodeType": "trigger.message",
            },
        },
        {
            "id": "intent",
            "type": "editable",
            "data": {
                "nodeType": "set.variable",
                "key": "intent",
                "value": intent,
            },
        },
        {
            "id": "extract_order_ref",
            "type": "editable",
            "data": {
                "nodeType": "customer_service.extract_order_ref",
                "input_from": "last",
                "save_as": "order_ref",
            },
        },
        {
            "id": "route_order_ref",
            "type": "editable",
            "data": {
                "nodeType": "router.rules",
                "rules": [
                    {
                        "when": "vars.order_ref_found == 'True'",
                        "route": "order_found",
                    }
                ],
                "default_route": "order_missing",
                "save_as": "order_ref_route",
            },
        },
        {
            "id": "set_missing_order_message",
            "type": "editable",
            "data": {
                "nodeType": "set.variable",
                "key": "final_message",
                "value": (
                    "Please provide the Shopify order number before this "
                    f"{action} request can be reviewed."
                ),
            },
        },
        {
            "id": "missing_order_response",
            "type": "editable",
            "data": {
                "nodeType": "response",
                "answer_from": "last",
            },
        },
        {
            "id": "get_order",
            "type": "editable",
            "data": {
                "nodeType": "shopify.get_order",
                "order_ref_from": "vars",
                "order_ref_key": "order_ref",
                "save_as": "shopify_order",
            },
        },
        {
            "id": "shopify_action",
            "type": "editable",
            "data": (
                {
                    "nodeType": "capability.invoke",
                    "config": {
                        "capability_id": "ecommerce.orders.action",
                        "payload": {
                            "action": action,
                            "reason": "Customer support workflow decision",
                        },
                        "input_from": "vars",
                        "input_key": "order_ref",
                        "save_as": "shopify_action",
                    },
                }
                if action == "cancel"
                else {
                    "nodeType": "shopify.order_action",
                    "action": action,
                    "order_ref_from": "vars",
                    "order_ref_key": "order_ref",
                    "reason": "Customer support workflow decision",
                    "save_as": "shopify_action",
                }
            ),
        },
        {
            "id": "set_success_message",
            "type": "editable",
            "data": {
                "nodeType": "set.variable",
                "key": "final_message",
                "value": response_message,
            },
        },
        {
            "id": "response",
            "type": "editable",
            "data": {
                "nodeType": "response",
                "answer_from": "last",
            },
        },
    ]

    edges = [
        {"source": "trigger", "target": "extract_order_ref"},
        {"source": "extract_order_ref", "target": "route_order_ref"},
        {
            "source": "route_order_ref",
            "target": "intent",
            "condition": "order_found",
        },
        {"source": "intent", "target": "get_order"},
        {
            "source": "route_order_ref",
            "target": "missing_order_response",
            "condition": "order_missing",
        },
        {"source": "get_order", "target": "shopify_action"},
        {"source": "shopify_action", "target": "response"},
    ]

    if requires_approval:
        approval_nodes = [
            {
                "id": "approval",
                "type": "editable",
                "data": {
                    "nodeType": "human.approval",
                    "question": (
                        f"Approve Shopify {action} action before execution?"
                    ),
                    "save_as": "approval_result",
                },
            },
            {
                "id": "route_approval",
                "type": "editable",
                "data": {
                    "nodeType": "router.rules",
                    "rules": [
                        {
                            "when": "vars.approval_result == 'True'",
                            "route": "approved",
                        }
                    ],
                    "default_route": "rejected",
                    "save_as": "approval_route",
                },
            },
            {
                "id": "set_rejected_message",
                "type": "editable",
                "data": {
                    "nodeType": "set.variable",
                    "key": "final_message",
                    "value": (
                        f"The Shopify {action} request was rejected. "
                        "No Shopify action was performed."
                    ),
                },
            },
            {
                "id": "rejected_response",
                "type": "editable",
                "data": {
                    "nodeType": "response",
                    "answer_from": "last",
                },
            },
        ]

        shopify_action_index = next(
            index
            for index, node in enumerate(nodes)
            if node["id"] == "shopify_action"
        )

        for offset, node in enumerate(approval_nodes):
            nodes.insert(shopify_action_index + offset, node)

        edges = [
            {"source": "trigger", "target": "extract_order_ref"},
            {"source": "extract_order_ref", "target": "route_order_ref"},
            {
                "source": "route_order_ref",
                "target": "intent",
                "condition": "order_found",
            },
            {"source": "intent", "target": "get_order"},
            {
                "source": "route_order_ref",
                "target": "set_missing_order_message",
                "condition": "order_missing",
            },
            {
                "source": "set_missing_order_message",
                "target": "missing_order_response",
            },
            {"source": "get_order", "target": "approval"},
            {"source": "approval", "target": "route_approval"},
            {
                "source": "route_approval",
                "target": "shopify_action",
                "condition": "approved",
            },
            {
                "source": "route_approval",
                "target": "set_rejected_message",
                "condition": "rejected",
            },
            {
                "source": "set_rejected_message",
                "target": "rejected_response",
            },
            {"source": "shopify_action", "target": "set_success_message"},
            {"source": "set_success_message", "target": "response"},
        ]

    if action == "refund":
        capture_node = {
            "id": "capture_customer_chat_session",
            "type": "editable",
            "data": {
                "nodeType": "context.extract",
                "source": "event_payload",
                "path": "session_id",
                "save_as": "customer_chat_session_id",
                "required": True,
            },
        }

        reply_rejection_node = {
            "id": "reply_rejection_to_customer",
            "type": "editable",
            "data": {
                "nodeType": "reply.customer_chat",
                "session_id_from": "vars",
                "session_id_key": "customer_chat_session_id",
                "message_from": "vars",
                "message_key": "final_message",
                "save_as": "customer_chat_delivery",
            },
        }

        reply_success_node = {
            "id": "reply_success_to_customer",
            "type": "editable",
            "data": {
                "nodeType": "reply.customer_chat",
                "session_id_from": "vars",
                "session_id_key": "customer_chat_session_id",
                "message_from": "vars",
                "message_key": "final_message",
                "save_as": "customer_chat_delivery",
            },
        }

        trigger_index = next(
            index
            for index, node in enumerate(nodes)
            if node["id"] == "trigger"
        )
        nodes.insert(trigger_index + 1, capture_node)

        rejected_response_index = next(
            index
            for index, node in enumerate(nodes)
            if node["id"] == "rejected_response"
        )
        nodes.insert(
            rejected_response_index,
            reply_rejection_node,
        )

        response_index = next(
            index
            for index, node in enumerate(nodes)
            if node["id"] == "response"
        )
        nodes.insert(
            response_index,
            reply_success_node,
        )

        for node in nodes:
            if node["id"] in {"response", "rejected_response"}:
                node["data"] = {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "final_message",
                }

        replacement_edges = []

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")

            if source == "trigger" and target == "extract_order_ref":
                replacement_edges.extend(
                    [
                        {
                            "source": "trigger",
                            "target": "capture_customer_chat_session",
                        },
                        {
                            "source": "capture_customer_chat_session",
                            "target": "extract_order_ref",
                        },
                    ]
                )
                continue

            if (
                source == "set_rejected_message"
                and target == "rejected_response"
            ):
                replacement_edges.extend(
                    [
                        {
                            "source": "set_rejected_message",
                            "target": "reply_rejection_to_customer",
                        },
                        {
                            "source": "reply_rejection_to_customer",
                            "target": "rejected_response",
                        },
                    ]
                )
                continue

            if source == "set_success_message" and target == "response":
                replacement_edges.extend(
                    [
                        {
                            "source": "set_success_message",
                            "target": "reply_success_to_customer",
                        },
                        {
                            "source": "reply_success_to_customer",
                            "target": "response",
                        },
                    ]
                )
                continue

            replacement_edges.append(edge)

        edges = replacement_edges

    return {
        "category": "shopify_support",
        "name": name,
        "description": description,
        "version": "1.3.0" if action == "refund" else "1.2.1",
        "tags": tags,
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "order_ref": {"type": "string"},
                "conversation_id": {"type": "string"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "order_ref": {"type": "string"},
                "shopify_order": {"type": "object"},
                "shopify_action": {"type": "object"},
                "approval_result": {"type": "boolean"},
                "requires_approval": {"type": "boolean"},
            },
        },
        "workflow_json": {
            "name": name,
            "nodes": nodes,
            "edges": edges,
        },
    }
