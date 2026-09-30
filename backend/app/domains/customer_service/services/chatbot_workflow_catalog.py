from __future__ import annotations


def website_chat_system_workflow_templates() -> list[dict]:
    return [
        {
            "category": "website_chat",
            "name": "Website Chat AI Reply Workflow",
            "description": (
                "Answers general website chat messages with AI and sends the reply "
                "back to the customer chat widget and Inbox."
            ),
            "tags": ["website_chat", "ai_reply", "customer_chat"],
            "version": "1.0.0",
            "workflow_json": {
                "name": "Website Chat AI Reply Workflow",
                "nodes": [
                    {"id": "trigger", "data": {"nodeType": "trigger.message"}},
                    {
                        "id": "generate_reply",
                        "data": {
                            "nodeType": "llm.generate",
                            "system": (
                                "You are Tajeran AI, a helpful ecommerce customer support assistant. "
                                "Answer clearly, politely, and briefly."
                            ),
                            "prompt": (
                                "Customer message: {{input}}\n\n"
                                "Write a helpful support reply for a Shopify store customer. Maximum 80 words. Do not write templates."
                            ),
                            "max_tokens": 180,
                            "role": "final",
                            "token_budget_mode": "cheap",
                            "save_as": "reply",
                            "provider_failure_fallback": (
                                "Our AI assistant is temporarily unavailable. "
                                "A human support agent will review your message."
                            ),
                        },
                    },
                    {
                        "id": "reply_customer",
                        "data": {
                            "nodeType": "reply.customer_chat",
                            "session_id_from": "extras",
                            "session_id_key": "session_id",
                            "message_from": "vars",
                            "message_key": "reply",
                        },
                    },
                    {"id": "response", "data": {"nodeType": "response"}},
                ],
                "edges": [
                    {"source": "trigger", "target": "generate_reply"},
                    {"source": "generate_reply", "target": "reply_customer"},
                    {"source": "reply_customer", "target": "response"},
                ],
            },
            "input_schema": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string"},
                    "customer_chat_reply_sent": {"type": "boolean"},
                },
            },
        },
        {
            "category": "website_chat",
            "name": "Website Chat Shopify Order Status Workflow",
            "description": (
                "Extracts an order number from website chat, looks up the real Shopify order, "
                "generates an order-aware answer, and replies in the widget and Inbox."
            ),
            "tags": ["website_chat", "shopify", "order_status", "customer_chat"],
            "version": "1.0.0",
            "workflow_json": {
                "name": "Website Chat Shopify Order Status Workflow",
                "nodes": [
                    {"id": "trigger", "data": {"nodeType": "trigger.message"}},
                    {
                        "id": "extract_order_ref",
                        "data": {
                            "nodeType": "customer_service.extract_order_ref",
                            "input_from": "last",
                            "save_as": "order_ref",
                        },
                    },
                    {
                        "id": "route",
                        "data": {
                            "nodeType": "router.rules",
                            "default_route": "general_chat",
                            "rules": [
                                {
                                    "when": "vars.order_ref_found == 'True'",
                                    "route": "order_found",
                                }
                            ],
                        },
                    },
                    {
                        "id": "get_order",
                        "data": {
                            "nodeType": "shopify.get_order",
                            "order_ref_from": "vars",
                            "order_ref_key": "order_ref",
                            "save_as": "shopify_order",
                        },
                    },
                    {
                        "id": "generate_order_reply",
                        "data": {
                            "nodeType": "llm.generate",
                            "system": (
                                "You are Tajeran AI, a Shopify customer support assistant. "
                                "Use ONLY the Shopify order summary provided. "
                                "Do not invent tracking, fulfillment, refund, cancellation, or delivery details. "
                                "Never claim you performed, submitted, recorded, escalated, or noted a Shopify action or support request "
                                "unless the workflow result explicitly confirms that action occurred. "
                                "Risky actions require human review."
                            ),
                            "prompt": (
                                "Customer message: {{input}}\n\n"
                                "Shopify order summary: {{vars.shopify_order.summary}}\n\n"
                                "Answer the customer's exact question first. "
                                "Do not include unrelated order details unless needed to explain the answer. "
                                "For simple factual questions, keep the answer under 35 words. "
                                "For broader questions, use at most 80 words. "
                                "Do not offer actions unless they require human review. "
                                "Use only this summary. Do not expose internal IDs unless needed. "
                                "Do not offer refunds, cancellations, address changes, or fulfillment as actions you can perform directly. "
                                "Do not say a request was noted, submitted, escalated, or sent to a team unless the provided workflow data confirms it. "
                                "If an action is available, say a support agent can review it."
                            ),
                            "save_as": "reply",
                            "provider_failure_fallback": (
                                "Our AI assistant is temporarily unavailable. "
                                "A human support agent will review your message."
                            ),
                        },
                    },
                    {
                        "id": "generate_general_reply",
                        "data": {
                            "nodeType": "llm.generate",
                            "system": (
                                "You are Tajeran AI, a helpful ecommerce support assistant."
                            ),
                            "prompt": (
                                "Customer message: {{input}}\n\n"
                                "Write a helpful support reply. Maximum 80 words. Do not write templates. "
                                "If the customer asks about an order without providing an order number, ask for the order number. "
                                "Say you can check fulfillment and tracking information. "
                                "Do not promise an ETA, delivery estimate, live location, refund, cancellation, or other information "
                                "unless it has been retrieved from a connected source."
                            ),
                            "save_as": "reply",
                            "provider_failure_fallback": (
                                "Our AI assistant is temporarily unavailable. "
                                "A human support agent will review your message."
                            ),
                        },
                    },
                    {
                        "id": "reply_customer",
                        "data": {
                            "nodeType": "reply.customer_chat",
                            "session_id_from": "extras",
                            "session_id_key": "session_id",
                            "message_from": "vars",
                            "message_key": "reply",
                        },
                    },
                    {"id": "response", "data": {"nodeType": "response"}},
                ],
                "edges": [
                    {"source": "trigger", "target": "extract_order_ref"},
                    {"source": "extract_order_ref", "target": "route"},
                    {
                        "source": "route",
                        "target": "get_order",
                        "condition": "order_found",
                    },
                    {
                        "source": "route",
                        "target": "generate_general_reply",
                        "condition": "general_chat",
                    },
                    {"source": "get_order", "target": "generate_order_reply"},
                    {"source": "generate_order_reply", "target": "reply_customer"},
                    {"source": "generate_general_reply", "target": "reply_customer"},
                    {"source": "reply_customer", "target": "response"},
                ],
            },
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "order_ref": {"type": "string"},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "order_ref": {"type": "string"},
                    "shopify_order": {"type": "object"},
                    "reply": {"type": "string"},
                    "customer_chat_reply_sent": {"type": "boolean"},
                },
            },
        },
    ]
