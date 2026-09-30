def build_reply_suggestion_workflow() -> dict:
    return {
        "nodes": [
            {
                "id": "trigger",
                "data": {
                    "nodeType": "trigger.message",
                    "input": "",
                },
            },
            {
                "id": "reply_agent",
                "data": {
                    "nodeType": "agent.custom",
                    "name": "Customer Service Reply Agent",
                    "role": "final",
                    "backend": "pure",
                    "pattern": "tool_agent",
                    "input_from": "last",
                    "input_key": "input",
                    "save_as": "reply_suggestion",
                    "tools": ["knowledge_search"],
                    "max_steps": 3,
                    "max_output_tokens": 300,
                    "token_budget_mode": "balanced",
                    "max_output_chars": 900,
                    "system_prompt": (
                        "You are a customer service reply assistant. "
                        "Write a concise, helpful customer-facing reply. "
                        "Use only the provided conversation context and policy facts. "
                        "Do not mention internal workflow, metadata, or reasoning."
                    ),
                },
            },
            {
                "id": "response",
                "data": {
                    "nodeType": "response",
                    "answer_from": "vars",
                    "answer_key": "reply_suggestion",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "trigger", "target": "reply_agent"},
            {"id": "e2", "source": "reply_agent", "target": "response"},
        ],
    }


def build_reply_suggestion_input(
    conversation, *, messages=None, workflow_meta=None
) -> str:
    latest_intent = None
    confidence = None

    if messages is None:
        messages = sorted(conversation.messages, key=lambda m: m.created_at)
    else:
        messages = sorted(messages, key=lambda m: m.created_at)

    workflow_meta = workflow_meta or {}

    if workflow_meta:
        classification = workflow_meta.get("classification") or {}
        latest_intent = classification.get("intent")
        confidence = classification.get("confidence")
    else:
        for message in reversed(messages):
            workflow = (message.meta or {}).get("workflow")
            if workflow:
                classification = workflow.get("classification") or {}
                latest_intent = classification.get("intent")
                confidence = classification.get("confidence")
                break

    lines = [
        "Customer service conversation:",
        f"Customer: {conversation.customer.name if conversation.customer else 'Unknown'}",
        f"Channel: {conversation.channel}",
        f"Subject: {conversation.subject or ''}",
        f"Detected intent: {latest_intent or 'general'}",
        f"Confidence: {confidence if confidence is not None else 'unknown'}",
        "",
        "Timeline:",
    ]

    for message in messages[-8:]:
        lines.append(f"- {message.sender_type}: {message.body}")

    return "\\n".join(lines)
