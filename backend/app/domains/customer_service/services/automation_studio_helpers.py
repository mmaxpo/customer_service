"""Pure graph and validation helpers for the automation studio."""

from __future__ import annotations

import json
import re
from typing import Any

from app.node_registration import register_application_nodes
from app.runtime.validation import validate_workflow
from app.runtime.nodes.registry.core import list_registered_nodes

NODE_LIBRARY: dict[str, tuple[str, str, str]] = {
    # node_type: (group, name, one-line description)
    "llm.generate": ("agents", "Write with AI", "Drafts text from a prompt and what earlier steps found."),
    "agent.custom": ("agents", "AI agent", "Works through a task with instructions and tools."),
    "router.llm": ("agents", "AI decides the path", "Picks the next branch from a list of choices."),
    "shopify.get_order": ("tools", "Find order", "Looks up the order in Shopify."),
    "shopify.order_action": ("tools", "Change the order", "Refunds, cancels, reships or changes the address in Shopify."),
    "customer_service.extract_order_ref": ("tools", "Find order number", "Reads the order number from the message."),
    "customer_service.load_conversation": ("tools", "Remember the conversation", "Reads the earlier messages so follow-up questions make sense."),
    "kb.search": ("tools", "Search knowledge", "Finds answers in your help articles and policies."),
    "reply.customer_chat": ("tools", "Reply in chat", "Sends a message to the customer."),
    "web.search": ("tools", "Search the web", "Looks something up on the web."),
    "router.rules": ("logic", "Condition", "Sends the conversation down a branch when a rule matches."),
    "human.approval": ("logic", "Human approval", "Waits for your team to approve before continuing."),
    "wait.time": ("logic", "Wait", "Pauses for a set time."),
    "set.variable": ("logic", "Remember a value", "Stores a value later steps can use."),
    "join.all": ("logic", "Wait for branches", "Continues once every branch before it has finished."),
    "control.loop": ("logic", "Repeat", "Repeats earlier steps up to a limit."),
}

MAX_OUTPUT_CHARS = 1200
_UNSUPPORTED_TEMPLATE = re.compile(r"\{\{\s*[#/^>]|\{\{\s*else\s*\}\}")

def humanize(node_id: str) -> str:
    words = re.sub(r"[_\-.]+", " ", node_id).strip()
    return words[:1].upper() + words[1:] if words else node_id

def node_type(node: dict) -> str:
    return str((node.get("data") or {}).get("nodeType") or node.get("type") or "")

def catalog() -> dict[str, dict]:
    register_application_nodes()
    return {item["node_type"]: item for item in list_registered_nodes()}

def graph_view(workflow: dict | None, catalog: dict[str, dict]) -> dict:
    workflow = workflow or {}
    nodes = []
    for node in workflow.get("nodes") or []:
        node_type_name = node_type(node)
        data = node.get("data") or {}
        entry = catalog.get(node_type_name) or {}
        nodes.append(
            {
                "id": str(node.get("id")),
                "type": node_type_name,
                "label": data.get("label") or humanize(str(node.get("id"))),
                "type_title": (NODE_LIBRARY.get(node_type_name) or (None, None))[1] or entry.get("title") or node_type_name,
                "category": entry.get("category"),
                "risk": entry.get("risk_level"),
            }
        )
    edges = [
        {
            "source": str(edge.get("source")),
            "target": str(edge.get("target")),
            "condition": edge.get("condition"),
        }
        for edge in workflow.get("edges") or []
    ]
    return {"nodes": nodes, "edges": edges}

def truncate(value: Any) -> Any:
    if value is None:
        return None
    raw = value if isinstance(value, str) else json.dumps(value, default=str)
    return raw if len(raw) <= MAX_OUTPUT_CHARS else raw[:MAX_OUTPUT_CHARS] + "…"

def diff(base: dict, proposed: dict) -> dict:
    base_nodes = {str(n.get("id")): n for n in base.get("nodes") or []}
    new_nodes = {str(n.get("id")): n for n in proposed.get("nodes") or []}
    return {
        "new": [i for i in new_nodes if i not in base_nodes],
        "removed": [i for i in base_nodes if i not in new_nodes],
        "changed": [
            i
            for i, node in new_nodes.items()
            if i in base_nodes
            and (node.get("data") or {}) != (base_nodes[i].get("data") or {})
        ],
    }

def needs_approval(node_type: str, entry: dict) -> bool:
    # The registry marks order/money/data-changing steps as "sensitive".
    return node_type != "human.approval" and entry.get("risk_level") == "sensitive"

def step_name(node: dict) -> str:
    return (node.get("data") or {}).get("label") or humanize(str(node.get("id")))

def validate(workflow: dict, catalog: dict[str, dict]) -> list[str]:
    errors = [error.message for error in validate_workflow(workflow, strict=True)]
    nodes = workflow.get("nodes") or []
    parents: dict[str, set[str]] = {}
    for edge in workflow.get("edges") or []:
        parents.setdefault(str(edge.get("target")), set()).add(str(edge.get("source")))
    types = {str(n.get("id")): node_type(n) for n in nodes}

    def has_approval_before(node_id: str, seen: set[str]) -> bool:
        for parent in parents.get(node_id, set()):
            if parent in seen:
                continue
            seen.add(parent)
            if types.get(parent) == "human.approval" or has_approval_before(parent, seen):
                return True
        return False

    for node in nodes:
        node_id = str(node.get("id"))
        current_type = types[node_id]
        entry = catalog.get(current_type)
        if entry is None:
            errors.append(f'"{step_name(node)}" uses a step type this workspace does not have ({current_type}).')
            continue
        if needs_approval(current_type, entry) and not has_approval_before(node_id, set()):
            errors.append(f'"{step_name(node)}" changes customer or order data and needs an approval step before it.')
        # The template engine only substitutes {{path}}; block helpers render as nothing.
        if any(
            isinstance(value, str) and _UNSUPPORTED_TEMPLATE.search(value)
            for value in (node.get("data") or {}).values()
        ):
            errors.append(
                f'"{step_name(node)}" uses a placeholder like {{{{#each}}}} or {{{{#if}}}} that isn\'t supported. '
                "Use {{input}} or {{vars.name}} instead."
            )
    return errors

def edit_summary(base: dict, proposed: dict, catalog: dict[str, dict]) -> list[dict]:
    changes = diff(base, proposed)
    nodes = {str(n.get("id")): n for n in proposed.get("nodes") or []}
    removed_nodes = {str(n.get("id")): n for n in base.get("nodes") or []}

    name = step_name
    lines = [{"kind": "new", "text": f"Adds a \"{name(nodes[i])}\" step."} for i in changes["new"]]
    lines += [{"kind": "changed", "text": f"Changes the settings of \"{name(nodes[i])}\"."} for i in changes["changed"]]
    lines += [{"kind": "changed", "text": f"Removes the \"{name(removed_nodes[i])}\" step."} for i in changes["removed"]]
    lines.append({"kind": "same", "text": "Everything else, including your workspace rules, stays the same."})
    return lines
