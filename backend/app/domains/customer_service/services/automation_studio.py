"""
Automation studio: the admin read model and change flow for customer-service
workflows.

A "workflow" here is an event subscription (what the dispatcher actually runs).
Versions and proposals reuse the core workflow_definitions/workflow_versions
tables: each subscription gets one definition, a proposal is a draft version,
and publishing makes that version live and copies its graph onto the
subscription so dispatch runs it.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.providers.llm.factory import build_generate_llm_client
from app.core.providers.llm.resilience import LLMProviderError
from app.domains.customer_service.models.omnichannel import (
    CustomerServiceEventSubscription,
)
from app.domains.customer_service.models.quality import CustomerServiceQualityReview
from app.domains.customer_service.models.workflows import (
    CustomerServiceWorkflowTemplate,
)
from app.node_registration import register_application_nodes
from app.runtime.validation import validate_workflow
from app.runtime.nodes.registry.core import list_registered_nodes
from app.workflow_operations.versions.repository import WorkflowVersionRepository

RUN_FLAG_REVIEW_TYPE = "run_flag"

# Extra node types a dry run never executes, on top of the runtime's own
# side-effect list: generic capability calls and tool-using agents can write,
# waits would stall, sub-workflows are not guarded here.
DRY_RUN_BLOCKED = {
    "capability.invoke",
    "agent.custom",
    "agent.langgraph",
    "agent.mcp",
    "subworkflow.call",
    "wait.time",
    "wait.event",
    "human.approval",
}
MAX_OUTPUT_CHARS = 1200


def _humanize(node_id: str) -> str:
    words = re.sub(r"[_\-.]+", " ", node_id).strip()
    return words[:1].upper() + words[1:] if words else node_id


def _node_type(node: dict) -> str:
    return str((node.get("data") or {}).get("nodeType") or node.get("type") or "")


# What a store admin can add from the graph editor, grouped the way the
# product talks about it. Internal/engine node types are left out.
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


def _catalog() -> dict[str, dict]:
    register_application_nodes()
    return {item["node_type"]: item for item in list_registered_nodes()}


def _graph_view(workflow: dict | None, catalog: dict[str, dict]) -> dict:
    workflow = workflow or {}
    nodes = []
    for node in workflow.get("nodes") or []:
        node_type = _node_type(node)
        data = node.get("data") or {}
        entry = catalog.get(node_type) or {}
        nodes.append(
            {
                "id": str(node.get("id")),
                "type": node_type,
                "label": data.get("label") or _humanize(str(node.get("id"))),
                "type_title": (NODE_LIBRARY.get(node_type) or (None, None))[1] or entry.get("title") or node_type,
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


def _truncate(value: Any) -> Any:
    if value is None:
        return None
    raw = value if isinstance(value, str) else json.dumps(value, default=str)
    return raw if len(raw) <= MAX_OUTPUT_CHARS else raw[:MAX_OUTPUT_CHARS] + "…"


def _diff(base: dict, proposed: dict) -> dict:
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


def _needs_approval(node_type: str, entry: dict) -> bool:
    # The registry marks order/money/data-changing steps as "sensitive".
    return node_type != "human.approval" and entry.get("risk_level") == "sensitive"


def _step_name(node: dict) -> str:
    return (node.get("data") or {}).get("label") or _humanize(str(node.get("id")))


def _validate(workflow: dict, catalog: dict[str, dict]) -> list[str]:
    errors = [error.message for error in validate_workflow(workflow, strict=True)]
    nodes = workflow.get("nodes") or []
    parents: dict[str, set[str]] = {}
    for edge in workflow.get("edges") or []:
        parents.setdefault(str(edge.get("target")), set()).add(str(edge.get("source")))
    types = {str(n.get("id")): _node_type(n) for n in nodes}

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
        node_type = types[node_id]
        entry = catalog.get(node_type)
        if entry is None:
            errors.append(f'"{_step_name(node)}" uses a step type this workspace does not have ({node_type}).')
            continue
        if _needs_approval(node_type, entry) and not has_approval_before(node_id, set()):
            errors.append(f'"{_step_name(node)}" changes customer or order data and needs an approval step before it.')
        # The template engine only substitutes {{path}}; block helpers render as nothing.
        if any(
            isinstance(value, str) and _UNSUPPORTED_TEMPLATE.search(value)
            for value in (node.get("data") or {}).values()
        ):
            errors.append(
                f'"{_step_name(node)}" uses a placeholder like {{{{#each}}}} or {{{{#if}}}} that isn\'t supported. '
                "Use {{input}} or {{vars.name}} instead."
            )
    return errors


_UNSUPPORTED_TEMPLATE = re.compile(r"\{\{\s*[#/^>]|\{\{\s*else\s*\}\}")


def _edit_summary(base: dict, proposed: dict, catalog: dict[str, dict]) -> list[dict]:
    diff = _diff(base, proposed)
    nodes = {str(n.get("id")): n for n in proposed.get("nodes") or []}
    removed_nodes = {str(n.get("id")): n for n in base.get("nodes") or []}

    name = _step_name
    lines = [{"kind": "new", "text": f"Adds a \"{name(nodes[i])}\" step."} for i in diff["new"]]
    lines += [{"kind": "changed", "text": f"Changes the settings of \"{name(nodes[i])}\"."} for i in diff["changed"]]
    lines += [{"kind": "changed", "text": f"Removes the \"{name(removed_nodes[i])}\" step."} for i in diff["removed"]]
    lines.append({"kind": "same", "text": "Everything else, including your workspace rules, stays the same."})
    return lines


def _parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(cleaned[start : end + 1])


# Topics a new workflow may be limited to. Cancellations and damaged items
# always go to a person, so they are not offered.
NEW_WORKFLOW_TOPICS = ("general", "shipping", "refund")

NEW_WORKFLOW_SYSTEM = (
    "You name a new customer-chat workflow and decide which messages it answers. "
    'Reply with JSON only: {"name": "<2-5 words>", "description": "<one sentence>", '
    '"topic": "general" | "shipping" | "refund" | null, '
    '"keywords": ["<3-8 short lowercase words or phrases a customer would type about this subject>"]}. '
    "The workflow runs when a customer message contains any keyword. Prefer short "
    "word stems (for example 'gift wrap') over long phrases. Use topic null unless "
    "the subject is clearly only shipping or only refunds."
)

# The smallest useful chat workflow; a new workflow is drafted as a change to it.
STARTER_WORKFLOW = {
    "name": "New workflow",
    "nodes": [
        {"id": "trigger", "data": {"nodeType": "trigger.message"}},
        {"id": "load_conversation", "data": {"nodeType": "customer_service.load_conversation", "save_as": "conversation"}},
        {"id": "search_knowledge", "data": {"nodeType": "kb.search", "k": 3, "query": "", "artifact_as": "kb_results"}},
        {
            "id": "generate_reply",
            "data": {
                "nodeType": "llm.generate",
                "save_as": "reply",
                "system": "You are a helpful ecommerce support assistant. Use only the help articles provided for facts.",
                "prompt": (
                    "Customer message: {{input}}\n\nEarlier messages in this conversation:\n{{vars.conversation}}\n\n"
                    "Help article hits: {{vars.kb_results}}\n\n"
                    "Answer the customer message. Use ONLY the help articles for facts. Maximum 80 words.\n\n"
                    "If the help articles do not answer the question: say you don't have that information, and that "
                    "you have passed the question to the team, who will reply here.\n\n"
                    "Hand-off rule: add [HANDOFF] at the very end ONLY when your reply says that you passed this to "
                    "the team or that a team member will reply.\n\n{{vars.reply_language_rule}}"
                ),
                "provider_failure_fallback": "Our AI assistant is temporarily unavailable. A human support agent will review your message.",
            },
        },
        {
            "id": "reply_customer",
            "data": {
                "nodeType": "reply.customer_chat",
                "message_key": "reply",
                "message_from": "vars",
                "session_id_key": "session_id",
                "session_id_from": "extras",
            },
        },
        {"id": "response", "data": {"nodeType": "response"}},
    ],
    "edges": [
        {"source": "trigger", "target": "load_conversation"},
        {"source": "load_conversation", "target": "search_knowledge"},
        {"source": "search_knowledge", "target": "generate_reply"},
        {"source": "generate_reply", "target": "reply_customer"},
        {"source": "reply_customer", "target": "response"},
    ],
}


def _keywords(value: Any) -> list[str]:
    words = [str(item).strip().lower()[:40] for item in value or [] if str(item).strip()]
    return list(dict.fromkeys(words))[:12]


PROPOSAL_SYSTEM = """You edit customer-service workflow graphs for a store owner.
A workflow is JSON: {"nodes":[{"id":str,"data":{"nodeType":str, ...config}}],
"edges":[{"source":id,"target":id,"condition"?:route}]}.
Rules:
- Make the smallest change that satisfies the request. Keep every unchanged node
  byte-for-byte identical, with the same id.
- New nodes get new snake_case ids. Only use node types from the catalog.
- Conditional edges ("condition") may only leave router.rules nodes; a
  router.rules node has "rules":[{"when": "<expr on vars>", "route": name}] and
  "default_route".
- Keep exactly one trigger.message node and a reachable response node.
- Any step that changes money, orders or customer data needs a human.approval
  node before it.
- Only use config keys listed for a node type in the catalog.
- Text settings (prompts, messages) support only simple placeholders:
  {{input}} for the customer's message and {{vars.<key>}} for a value an
  earlier step saved (a list is inserted whole). No loops, conditions or
  helpers such as {{#each}} or {{#if}}.
- A prompt that may tell the customer a person will follow up (the question
  isn't covered, or the customer asks for a human) must instruct the model to
  end that reply with [HANDOFF]. The marker is hidden from the customer and
  flags the case for the team.
Return ONLY JSON: {"workflow": {...}, "summary": [{"kind": "new"|"changed"|"same",
"text": "<one plain sentence a shop owner understands>"}]}.
Summary: one line per new or changed step, then one "same" line about what
stays the same. No internal ids or type names in summary text."""


class AutomationStudioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.versions = WorkflowVersionRepository(db)

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------

    async def _subscriptions(self, workspace_id: UUID):
        rows = await self.db.execute(
            select(CustomerServiceEventSubscription, CustomerServiceWorkflowTemplate)
            .outerjoin(
                CustomerServiceWorkflowTemplate,
                CustomerServiceWorkflowTemplate.id
                == CustomerServiceEventSubscription.workflow_template_id,
            )
            .where(CustomerServiceEventSubscription.user_id == workspace_id)
            .order_by(CustomerServiceEventSubscription.created_at)
        )
        return rows.all()

    async def _subscription(self, workspace_id: UUID, subscription_id: UUID):
        for subscription, template in await self._subscriptions(workspace_id):
            if subscription.id == subscription_id:
                return subscription, template
        raise HTTPException(status_code=404, detail="Workflow not found")

    @staticmethod
    def _live_graph(subscription, template) -> dict:
        return subscription.workflow_json or (template.workflow_json if template else {}) or {}

    async def overview(self, *, workspace_id: UUID) -> dict:
        catalog = _catalog()
        stats = await self._run_stats(workspace_id)
        routing = await self._routing_stats(workspace_id)
        drafts = await self._open_proposals(workspace_id)

        workflows = []
        for subscription, template in await self._subscriptions(workspace_id):
            meta = subscription.meta or {}
            sub_stats = stats.get(str(subscription.id), {})
            edited = max(
                [d for d in [subscription.updated_at, template.updated_at if template else None] if d]
            )
            workflows.append(
                {
                    "id": str(subscription.id),
                    "name": subscription.name,
                    "description": template.description if template else meta.get("description"),
                    "enabled": subscription.is_active,
                    "keywords": (subscription.filters or {}).get("keywords") or [],
                    # Only workflows made from a prompt can be switched on and off here.
                    "can_toggle": meta.get("source") == "studio_prompt",
                    "live_version": meta.get("live_version"),
                    "dispatch_mode": meta.get("dispatch_mode") or "standard",
                    "graph": _graph_view(self._live_graph(subscription, template), catalog),
                    "runs_7d": sub_stats.get("runs", 0),
                    "answered_7d": sub_stats.get("answered", 0),
                    "edited_at": edited,
                    "open_proposal_id": drafts.get(str(subscription.id)),
                }
            )

        return {"workflows": workflows, "routing": routing}

    async def workflow_detail(self, *, workspace_id: UUID, subscription_id: UUID) -> dict:
        subscription, template = await self._subscription(workspace_id, subscription_id)
        meta = subscription.meta or {}
        workflow = self._live_graph(subscription, template)
        if meta.get("definition_id"):
            live = await self.versions.get_active_version(definition_id=UUID(meta["definition_id"]))
            if live:
                workflow = live["workflow_json"]
        drafts = await self._open_proposals(workspace_id)
        return {
            "id": str(subscription.id),
            "name": subscription.name,
            "live_version": meta.get("live_version"),
            "workflow": workflow,
            "open_proposal_id": drafts.get(str(subscription.id)),
        }

    async def node_library(self, *, workspace_id: UUID) -> list[dict]:
        from app.domains.customer_service.repositories.shopify import ShopifyRepository

        has_shopify = bool(
            await ShopifyRepository(self.db).list_active_connections(user_id=workspace_id)
        )
        catalog = _catalog()
        items = []
        for node_type, (group, name, description) in NODE_LIBRARY.items():
            entry = catalog.get(node_type)
            if entry is None or (node_type.startswith("shopify.") and not has_shopify):
                continue
            items.append(
                {
                    "node_type": node_type,
                    "group": group,
                    "name": name,
                    "description": description,
                    "needs_approval": _needs_approval(node_type, entry),
                    "default_config": entry.get("default_config") or {},
                    "schema": entry.get("schema") or {},
                }
            )
        return items

    async def _run_stats(self, workspace_id: UUID) -> dict[str, dict]:
        # A run counts as answered when it finished and no step asked for a
        # human handoff (degraded LLM, fallback reply).
        result = await self.db.execute(
            text(
                """
                SELECT j.payload->'extras'->'subscription'->>'id' AS subscription_id,
                       count(*) AS runs,
                       count(*) FILTER (
                         WHERE r.status = 'done' AND NOT EXISTS (
                           SELECT 1 FROM workflow_run_events e
                           WHERE e.workflow_run_id = r.workflow_run_id
                             AND e.event->'meta'->>'handoff_required' = 'true'
                         )
                       ) AS answered
                FROM platform_jobs j
                LEFT JOIN workflow_runs r
                  ON r.workflow_run_id::text = j.result->'meta'->>'workflow_run_id'
                WHERE j.user_id = :workspace_id
                  AND j.job_type = 'workflow.run'
                  AND j.created_at > now() - interval '7 days'
                  AND j.payload->'extras'->'subscription'->>'id' IS NOT NULL
                GROUP BY 1
                """
            ),
            {"workspace_id": workspace_id},
        )
        return {
            row.subscription_id: {"runs": row.runs, "answered": row.answered}
            for row in result
        }

    async def _routing_stats(self, workspace_id: UUID) -> dict:
        result = await self.db.execute(
            text(
                """
                SELECT count(*) AS messages,
                       count(*) FILTER (WHERE NOT EXISTS (
                         SELECT 1 FROM platform_jobs j
                         WHERE j.user_id = :workspace_id
                           AND j.job_type = 'workflow.run'
                           AND j.payload->'extras'->'event'->'payload'->>'inbox_message_id' = m.id::text
                       )) AS unmatched
                FROM cs_conversation_messages m
                JOIN cs_conversations c ON c.id = m.conversation_id
                WHERE c.user_id = :workspace_id
                  AND m.sender_type = 'customer'
                  AND m.created_at > now() - interval '7 days'
                """
            ),
            {"workspace_id": workspace_id},
        )
        row = result.one()
        return {"messages_7d": row.messages, "unmatched_7d": row.unmatched}

    async def _open_proposals(self, workspace_id: UUID) -> dict[str, str]:
        result = await self.db.execute(
            text(
                """
                SELECT d.metadata_json->>'subscription_id' AS subscription_id, v.id
                FROM workflow_versions v
                JOIN workflow_definitions d ON d.id = v.workflow_definition_id
                WHERE d.user_id = :workspace_id
                  AND v.status = 'draft'
                  AND v.metadata_json->>'kind' = 'proposal'
                ORDER BY v.created_at
                """
            ),
            {"workspace_id": workspace_id},
        )
        return {row.subscription_id: str(row.id) for row in result}

    # ------------------------------------------------------------------
    # Proposals
    # ------------------------------------------------------------------

    async def _ensure_definition(self, workspace_id: UUID, subscription, template) -> dict:
        meta = dict(subscription.meta or {})
        if meta.get("definition_id"):
            definition = await self.versions.get_definition(
                definition_id=UUID(meta["definition_id"])
            )
            if definition and definition["user_id"] == workspace_id:
                return definition

        definition = await self.versions.create_definition(
            user_id=workspace_id,
            name=subscription.name,
            slug=f"cs-subscription-{subscription.id}",
            description=template.description if template else None,
            metadata_json={"subscription_id": str(subscription.id)},
        )
        first = await self.versions.create_version(
            definition_id=definition["id"],
            user_id=workspace_id,
            workflow_json=self._live_graph(subscription, template),
            notes="Imported from the running workflow",
            evaluation_summary={},
            metadata_json={"kind": "import"},
        )
        await self.versions.publish_version(
            definition_id=definition["id"], version=first["version"]
        )
        subscription.meta = {
            **meta,
            "definition_id": str(definition["id"]),
            "live_version": first["version"],
        }
        await self.db.commit()
        return await self.versions.get_definition(definition_id=definition["id"])

    async def _generate(self, *, base: dict, requests: list[str], catalog: dict) -> dict:
        used = {_node_type(n) for n in base.get("nodes") or []}
        catalog_lines = [
            f'- {t}: {e.get("title")} ({e.get("category")}; risk {e.get("risk_level")}'
            + ("; needs a human.approval before it" if _needs_approval(t, e) else "")
            + ")"
            + (
                # Exact config keys (with their descriptions) for any step the
                # draft may add, so the model doesn't invent settings.
                " config: "
                + "; ".join(
                    f'{key}' + (f' ({prop["description"]})' if prop.get("description") else "")
                    for key, prop in sorted((e.get("schema") or {}).get("properties", {}).items())
                    if key not in {"nodeType", "node_type", "name", "label"}
                )
                if t in used or t in NODE_LIBRARY or e.get("category") in {"logic", "control"}
                else ""
            )
            for t, e in sorted(catalog.items())
        ]
        prompt = (
            "Node catalog:\n"
            + "\n".join(catalog_lines)
            + "\n\nCurrent workflow:\n"
            + json.dumps(base, ensure_ascii=False)
            + "\n\nRequested changes, in order (later ones refine earlier ones):\n"
            + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(requests))
        )
        try:
            result = await build_generate_llm_client().generate(
                prompt=prompt, system=PROPOSAL_SYSTEM, max_tokens=6000
            )
        except LLMProviderError as exc:
            raise HTTPException(
                status_code=503,
                detail="TCOS can't draft changes right now because the AI provider is unavailable. Try again in a few minutes.",
            ) from exc
        try:
            parsed = _parse_json(result.text)
        except ValueError as exc:  # includes JSONDecodeError
            raise HTTPException(
                status_code=502,
                detail="TCOS could not draft this change. Try rephrasing it.",
            ) from exc

        workflow = parsed.get("workflow")
        if not isinstance(workflow, dict):
            raise HTTPException(status_code=502, detail="TCOS returned no workflow.")
        summary = [
            {"kind": s.get("kind"), "text": str(s.get("text") or "")}
            for s in parsed.get("summary") or []
            if isinstance(s, dict) and s.get("kind") in {"new", "changed", "same"}
        ]
        return {"workflow": workflow, "summary": summary}

    async def create_proposal(
        self,
        *,
        workspace_id: UUID,
        subscription_id: UUID,
        request: str | None = None,
        workflow: dict | None = None,
    ) -> dict:
        """Typed changes (request) and graph edits (workflow) become the same
        draft version and go through the same validation and publish."""
        subscription, template = await self._subscription(workspace_id, subscription_id)
        definition = await self._ensure_definition(workspace_id, subscription, template)
        live = await self.versions.get_active_version(definition_id=definition["id"])
        base = live["workflow_json"]
        catalog = _catalog()
        if workflow is not None:
            drafted = {"workflow": workflow, "summary": _edit_summary(base, workflow, catalog)}
            request = request or "Edited on the graph"
        else:
            drafted = await self._generate(base=base, requests=[request], catalog=catalog)

        version = await self.versions.create_version(
            definition_id=definition["id"],
            user_id=workspace_id,
            workflow_json=drafted["workflow"],
            notes=request,
            evaluation_summary={},
            metadata_json={
                "kind": "proposal",
                "subscription_id": str(subscription.id),
                "base_version": live["version"],
                "requests": [request],
                "summary": drafted["summary"],
            },
        )
        return await self.get_proposal(workspace_id=workspace_id, proposal_id=version["id"])

    # ------------------------------------------------------------------
    # New workflow from a prompt
    # ------------------------------------------------------------------

    async def draft_workflow(self, *, request: str) -> dict:
        """Draft a new chat workflow from a typed request. Nothing is saved."""
        catalog = _catalog()
        drafted = await self._generate(base=STARTER_WORKFLOW, requests=[request], catalog=catalog)
        try:
            result = await build_generate_llm_client().generate(
                prompt=f"The store owner asked for this new workflow:\n{request}",
                system=NEW_WORKFLOW_SYSTEM,
                max_tokens=400,
            )
            routing = _parse_json(result.text)
        except LLMProviderError as exc:
            raise HTTPException(
                status_code=503,
                detail="TCOS can't draft a workflow right now because the AI provider is unavailable. Try again in a few minutes.",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="TCOS could not draft this workflow. Try rephrasing it.") from exc

        topic = routing.get("topic")
        return {
            "name": str(routing.get("name") or "New workflow")[:120],
            "description": str(routing.get("description") or "")[:500],
            "topic": topic if topic in NEW_WORKFLOW_TOPICS else None,
            "keywords": _keywords(routing.get("keywords")),
            "workflow": drafted["workflow"],
            "graph": _graph_view(drafted["workflow"], catalog),
            "validation_errors": _validate(drafted["workflow"], catalog),
        }

    async def create_workflow(
        self,
        *,
        workspace_id: UUID,
        name: str,
        description: str,
        topic: str | None,
        keywords: list[str],
        workflow: dict,
    ) -> dict:
        """Save a drafted workflow, switched off. It must say when it runs:
        a workflow with no keywords would take every customer message."""
        keywords = _keywords(keywords)
        if not keywords:
            raise HTTPException(status_code=422, detail="Add at least one keyword so the workflow knows which messages to answer.")
        if topic is not None and topic not in NEW_WORKFLOW_TOPICS:
            raise HTTPException(status_code=422, detail="Unknown topic.")
        errors = _validate(workflow, _catalog())
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})

        subscription = CustomerServiceEventSubscription(
            user_id=workspace_id,
            name=name.strip()[:120] or "New workflow",
            event_type="customer.chat.message.created",
            channel="website",
            workflow_json=workflow,
            filters={"keywords": keywords, **({"intent": topic} if topic else {})},
            is_active=False,
            meta={"source": "studio_prompt", "description": description.strip()[:500], "dispatch_mode": "standard"},
        )
        self.db.add(subscription)
        await self.db.commit()
        return {"workflow_id": str(subscription.id)}

    async def set_workflow_enabled(self, *, workspace_id: UUID, subscription_id: UUID, enabled: bool) -> dict:
        subscription = await self._prompt_workflow(workspace_id, subscription_id)
        subscription.is_active = enabled
        await self.db.commit()
        return {"workflow_id": str(subscription.id), "enabled": enabled}

    async def _prompt_workflow(self, workspace_id: UUID, subscription_id: UUID):
        subscription, _ = await self._subscription(workspace_id, subscription_id)
        if (subscription.meta or {}).get("source") != "studio_prompt":
            raise HTTPException(status_code=409, detail="This workflow can't be changed here.")
        return subscription

    async def set_workflow_keywords(self, *, workspace_id: UUID, subscription_id: UUID, keywords: list[str]) -> dict:
        subscription = await self._prompt_workflow(workspace_id, subscription_id)
        keywords = _keywords(keywords)
        if not keywords:
            raise HTTPException(status_code=422, detail="Add at least one keyword so the workflow knows which messages to answer.")
        subscription.filters = {**(subscription.filters or {}), "keywords": keywords}
        await self.db.commit()
        return {"workflow_id": str(subscription.id), "keywords": keywords}

    async def delete_workflow(self, *, workspace_id: UUID, subscription_id: UUID) -> None:
        subscription = await self._prompt_workflow(workspace_id, subscription_id)
        if subscription.is_active:
            raise HTTPException(status_code=409, detail="Turn this workflow off before deleting it.")
        await self.db.delete(subscription)
        await self.db.commit()

    async def _proposal_row(self, workspace_id: UUID, proposal_id: UUID) -> dict:
        result = await self.db.execute(
            text(
                """
                SELECT v.*, d.metadata_json AS definition_meta, d.active_version
                FROM workflow_versions v
                JOIN workflow_definitions d ON d.id = v.workflow_definition_id
                WHERE v.id = :id AND d.user_id = :workspace_id
                  AND v.metadata_json->>'kind' = 'proposal'
                """
            ),
            {"id": proposal_id, "workspace_id": workspace_id},
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return dict(row)

    async def get_proposal(self, *, workspace_id: UUID, proposal_id: UUID) -> dict:
        row = await self._proposal_row(workspace_id, proposal_id)
        meta = row["metadata_json"] or {}
        subscription, _ = await self._subscription(
            workspace_id, UUID(meta["subscription_id"])
        )
        base = await self.versions.get_version(
            definition_id=row["workflow_definition_id"], version=meta["base_version"]
        )
        catalog = _catalog()
        proposed = row["workflow_json"]
        return {
            "id": str(row["id"]),
            "workflow_id": str(subscription.id),
            "workflow_name": subscription.name,
            "version": row["version"],
            "base_version": meta["base_version"],
            "live_version": row["active_version"],
            "status": row["status"],
            "requests": meta.get("requests") or [],
            "summary": meta.get("summary") or [],
            "graph": _graph_view(proposed, catalog),
            "base_graph": _graph_view(base["workflow_json"] if base else {}, catalog),
            "diff": _diff(base["workflow_json"] if base else {}, proposed),
            "validation_errors": _validate(proposed, catalog),
            "test_results": row["evaluation_summary"] or None,
            "recent_conversations": await self._recent_conversations(
                workspace_id, subscription.id
            ),
        }

    async def refine_proposal(
        self, *, workspace_id: UUID, proposal_id: UUID, request: str
    ) -> dict:
        row = await self._proposal_row(workspace_id, proposal_id)
        if row["status"] != "draft":
            raise HTTPException(status_code=409, detail="This proposal is no longer a draft.")
        meta = dict(row["metadata_json"] or {})
        base = await self.versions.get_version(
            definition_id=row["workflow_definition_id"], version=meta["base_version"]
        )
        requests = [*(meta.get("requests") or []), request]
        drafted = await self._generate(
            base=base["workflow_json"], requests=requests, catalog=_catalog()
        )
        meta.update({"requests": requests, "summary": drafted["summary"]})
        await self.db.execute(
            text(
                """
                UPDATE workflow_versions
                SET workflow_json = CAST(:workflow AS jsonb),
                    metadata_json = CAST(:meta AS jsonb),
                    evaluation_summary = '{}'::jsonb
                WHERE id = :id AND status = 'draft'
                """
            ),
            {
                "id": proposal_id,
                "workflow": json.dumps(drafted["workflow"], ensure_ascii=False),
                "meta": json.dumps(meta, ensure_ascii=False, default=str),
            },
        )
        await self.db.commit()
        return await self.get_proposal(workspace_id=workspace_id, proposal_id=proposal_id)

    async def publish_proposal(self, *, workspace_id: UUID, proposal_id: UUID) -> dict:
        row = await self._proposal_row(workspace_id, proposal_id)
        if row["status"] != "draft":
            raise HTTPException(status_code=409, detail="This proposal is no longer a draft.")
        errors = _validate(row["workflow_json"], _catalog())
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})
        tests = row["evaluation_summary"] or {}
        if not tests.get("tested_at"):
            raise HTTPException(status_code=409, detail="Test this change on past conversations before publishing.")
        if any(not c.get("passed") and not c.get("provider_unavailable") for c in tests.get("cases") or []):
            raise HTTPException(status_code=409, detail="Some past conversations failed with this change. Fix it before publishing.")
        cases = tests.get("cases") or []
        if cases and all(c.get("provider_unavailable") for c in cases):
            raise HTTPException(status_code=409, detail="None of the past conversations could run because the AI provider is unavailable. Test again once it's back.")

        subscription, _ = await self._subscription(
            workspace_id, UUID(row["metadata_json"]["subscription_id"])
        )
        await self.versions.publish_version(
            definition_id=row["workflow_definition_id"], version=row["version"]
        )
        subscription.workflow_json = row["workflow_json"]
        subscription.meta = {**(subscription.meta or {}), "live_version": row["version"]}
        await self.db.commit()
        return {"workflow_id": str(subscription.id), "live_version": row["version"]}

    async def discard_proposal(self, *, workspace_id: UUID, proposal_id: UUID) -> None:
        await self._proposal_row(workspace_id, proposal_id)
        await self.db.execute(
            text("UPDATE workflow_versions SET status = 'discarded' WHERE id = :id AND status = 'draft'"),
            {"id": proposal_id},
        )
        await self.db.commit()

    # ------------------------------------------------------------------
    # Test replay (dry run)
    # ------------------------------------------------------------------

    async def _dry_run(self, *, workspace_id: UUID, workflow: dict, message: str) -> dict:
        """Run a draft on a past customer message with every side effect
        blocked. Nothing is persisted and nothing reaches the customer."""
        from types import SimpleNamespace
        from uuid import uuid4

        from app.runtime.execution import execute_workflow_dag
        from app.runtime.state.run_state import new_run_state
        from app.runtime.tools import build_tools
        from app.runtime_services import build_application_runtime_context

        register_application_nodes()
        guarded = json.loads(json.dumps(workflow))
        for node in guarded.get("nodes") or []:
            if _node_type(node) in DRY_RUN_BLOCKED:
                node.setdefault("data", {})["replay_policy"] = "skip"

        tools = build_tools()
        ctx = build_application_runtime_context(
            request=SimpleNamespace(
                state=SimpleNamespace(tools=tools),
                app=SimpleNamespace(state=SimpleNamespace(tools=tools)),
            ),
            user_id=workspace_id,
            thread_id=uuid4(),
            db=self.db,
            extras={"customer_service": True, "dry_run": True},
            run_store=None,
            event_sink=None,
        )
        result = await execute_workflow_dag(
            ctx=ctx,
            workflow=guarded,
            message=message,
            replay_state=new_run_state(message),
        )
        meta = result.get("meta") or {}
        state = meta.get("final_state") or {}
        nodes = {str(n.get("id")): n for n in guarded.get("nodes") or []}
        skipped = (state.get("meta") or {}).get("replay", {}).get("skipped_side_effect_nodes", [])

        answer = None
        for item in skipped:
            data = (nodes.get(item["node_id"]) or {}).get("data") or {}
            if item.get("node_type") != "reply.customer_chat":
                continue
            source = data.get("message_from", "last")
            if source == "config":
                answer = data.get("message")
            elif source == "vars":
                answer = (state.get("vars") or {}).get(data.get("message_key", "reply"))
            else:
                answer = state.get("last")
        if answer is None and isinstance(result.get("answer"), str):
            answer = result["answer"]

        node_meta = (state.get("meta") or {}).get("node_meta_by_id") or {}
        return {
            "status": meta.get("status"),
            "error": meta.get("error"),
            # The customer never sees the hand-off marker, so the preview hides it too.
            "answer": answer.replace("[HANDOFF]", "").strip() if isinstance(answer, str) else None,
            "handed_over": isinstance(answer, str) and "[HANDOFF]" in answer,
            "fallback_used": any((m or {}).get("handoff_required") for m in node_meta.values()),
            "blocked_steps": [
                (nodes.get(item["node_id"]) or {}).get("data", {}).get("label")
                or _humanize(item["node_id"])
                for item in skipped
            ],
        }

    async def test_proposal(self, *, workspace_id: UUID, proposal_id: UUID) -> dict:
        row = await self._proposal_row(workspace_id, proposal_id)
        subscription_id = UUID(row["metadata_json"]["subscription_id"])
        conversations = [
            c
            for c in await self._recent_conversations(workspace_id, subscription_id)
            if c["customer_message"]
        ]
        cases = []
        for conversation in conversations:
            try:
                outcome = await self._dry_run(
                    workspace_id=workspace_id,
                    workflow=row["workflow_json"],
                    message=conversation["customer_message"],
                )
            except Exception as exc:  # a broken draft must not break the page
                outcome = {"status": "error", "error": str(exc), "answer": None, "fallback_used": False, "blocked_steps": []}
            provider_down = "llm_" in str(outcome["error"] or "").lower()
            before = (conversation["answer"] or "").strip()
            after = (outcome["answer"] or "").strip()
            cases.append(
                {
                    **conversation,
                    "draft_status": outcome["status"],
                    "draft_error": _truncate(outcome["error"]),
                    "draft_answer": outcome["answer"],
                    "draft_handed_over": outcome.get("handed_over", False),
                    "fallback_used": outcome["fallback_used"],
                    "blocked_steps": outcome["blocked_steps"],
                    "provider_unavailable": provider_down,
                    "passed": outcome["status"] == "ok" and not outcome["error"],
                    "changed": bool(after) and after != before,
                }
            )
        results = {
            "tested_at": datetime.now(timezone.utc).isoformat(),
            "total": len(cases),
            "passed": sum(1 for c in cases if c["passed"]),
            "changed": sum(1 for c in cases if c["changed"]),
            "untested": sum(1 for c in cases if c["provider_unavailable"]),
            "cases": cases,
        }
        await self.db.execute(
            text("UPDATE workflow_versions SET evaluation_summary = CAST(:r AS jsonb) WHERE id = :id"),
            {"id": proposal_id, "r": json.dumps(results, default=str)},
        )
        await self.db.commit()
        return json.loads(json.dumps(results, default=str))

    # ------------------------------------------------------------------
    # Version history
    # ------------------------------------------------------------------

    async def version_history(self, *, workspace_id: UUID, subscription_id: UUID) -> dict:
        subscription, _ = await self._subscription(workspace_id, subscription_id)
        meta = subscription.meta or {}
        versions = []
        if meta.get("definition_id"):
            rows = await self.versions.list_versions(definition_id=UUID(meta["definition_id"]))
            versions = [
                {
                    "id": str(row["id"]),
                    "version": row["version"],
                    "status": row["status"],
                    "kind": (row["metadata_json"] or {}).get("kind"),
                    "note": row["notes"],
                    "summary": (row["metadata_json"] or {}).get("summary") or [],
                    "created_at": row["created_at"],
                    "published_at": row["published_at"],
                }
                for row in rows
                if row["status"] != "discarded"
            ]
        return {
            "workflow_id": str(subscription.id),
            "workflow_name": subscription.name,
            "live_version": meta.get("live_version"),
            "versions": versions,
        }

    async def restore_version(
        self, *, workspace_id: UUID, subscription_id: UUID, version: int
    ) -> dict:
        """Make an earlier published version live again (undo)."""
        subscription, _ = await self._subscription(workspace_id, subscription_id)
        meta = subscription.meta or {}
        if not meta.get("definition_id"):
            raise HTTPException(status_code=404, detail="This workflow has no version history yet.")
        definition_id = UUID(meta["definition_id"])
        target = await self.versions.get_version(definition_id=definition_id, version=version)
        if target is None or target["status"] not in {"published", "archived"}:
            raise HTTPException(status_code=409, detail="Only versions that were live can be restored.")

        await self.versions.publish_version(definition_id=definition_id, version=version)
        subscription.workflow_json = target["workflow_json"]
        subscription.meta = {**meta, "live_version": version}
        await self.db.commit()
        return {"workflow_id": str(subscription.id), "live_version": version}

    async def _recent_conversations(self, workspace_id: UUID, subscription_id: UUID) -> list[dict]:
        # Real past answers from this workflow, shown as the "before" side.
        result = await self.db.execute(
            text(
                """
                SELECT r.workflow_run_id, r.thread_id, r.status, r.created_at,
                  (SELECT m.body FROM cs_conversation_messages m
                    WHERE m.conversation_id = r.thread_id AND m.sender_type = 'customer'
                      AND m.created_at <= r.created_at
                    ORDER BY m.created_at DESC LIMIT 1) AS customer_message,
                  (SELECT m.body FROM cs_conversation_messages m
                    WHERE m.conversation_id = r.thread_id AND m.sender_type = 'ai'
                      AND m.created_at >= r.created_at
                    ORDER BY m.created_at ASC LIMIT 1) AS answer
                FROM platform_jobs j
                JOIN workflow_runs r
                  ON r.workflow_run_id::text = j.result->'meta'->>'workflow_run_id'
                WHERE j.user_id = :workspace_id
                  AND j.job_type = 'workflow.run'
                  AND j.payload->'extras'->'subscription'->>'id' = :subscription_id
                ORDER BY r.created_at DESC
                LIMIT 5
                """
            ),
            {"workspace_id": workspace_id, "subscription_id": str(subscription_id)},
        )
        return [
            {
                "run_id": str(row.workflow_run_id),
                "conversation_id": str(row.thread_id) if row.thread_id else None,
                "status": row.status,
                "created_at": row.created_at,
                "customer_message": row.customer_message,
                "answer": row.answer,
            }
            for row in result
        ]

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    _RUNS_SQL = """
        SELECT r.workflow_run_id, r.thread_id, r.status, r.created_at, r.updated_at,
               r.extra, job.subscription_id, job.subscription_name, job.version,
               job.customer_message, job.final_run_id,
               EXISTS (
                 SELECT 1 FROM workflow_run_events e
                 WHERE e.workflow_run_id = r.workflow_run_id
                   AND (e.event->'meta'->>'handoff_required' = 'true'
                        OR e.event->>'event' = 'node_error')
               ) AS had_problem,
               (SELECT count(*) FROM cs_quality_reviews q
                 WHERE q.user_id = r.user_id AND q.review_type = :flag_type
                   AND q.outcome = 'open'
                   AND q.issues->0->>'run_id' = r.workflow_run_id::text) AS open_flags,
               EXISTS (SELECT 1 FROM cs_quality_reviews q
                 WHERE q.user_id = r.user_id AND q.review_type = :flag_type
                   AND q.outcome = 'dismissed'
                   AND q.issues->0->>'run_id' = r.workflow_run_id::text) AS dismissed
        FROM workflow_runs r
        LEFT JOIN LATERAL (
          SELECT j.payload->'extras'->'subscription'->>'id' AS subscription_id,
                 j.payload->'extras'->'subscription'->>'name' AS subscription_name,
                 j.payload->'extras'->'workflow_version' AS version,
                 j.payload->>'message' AS customer_message,
                 j.result->'meta'->>'workflow_run_id' AS final_run_id
          FROM platform_jobs j
          WHERE j.user_id = r.user_id AND j.job_type = 'workflow.run'
            AND (j.result->'meta'->>'workflow_run_id' = r.workflow_run_id::text
                 OR (j.payload->>'thread_id' = r.thread_id::text
                     AND j.created_at <= r.created_at))
          ORDER BY (j.result->'meta'->>'workflow_run_id' = r.workflow_run_id::text) DESC NULLS LAST,
                   j.created_at DESC
          LIMIT 1
        ) job ON true
        WHERE r.user_id = :workspace_id
    """

    @staticmethod
    def _run_summary(row) -> dict:
        reasons = []
        if row.open_flags:
            reasons.append("flagged")
        if not row.dismissed:
            if row.status == "failed":
                reasons.append("failed")
            elif row.had_problem:
                reasons.append("handed_over")
        return {
            "run_id": str(row.workflow_run_id),
            "conversation_id": str(row.thread_id) if row.thread_id else None,
            "status": row.status,
            "workflow_id": row.subscription_id,
            "workflow_name": row.subscription_name,
            "version": row.version,
            "created_at": row.created_at,
            "customer_message": _truncate(row.customer_message),
            "review_reasons": reasons,
        }

    async def review_queue(self, *, workspace_id: UUID) -> list[dict]:
        result = await self.db.execute(
            text(
                self._RUNS_SQL
                + """
                  AND r.created_at > now() - interval '30 days'
                ORDER BY r.created_at DESC
                LIMIT 100
                """
            ),
            {"workspace_id": workspace_id, "flag_type": RUN_FLAG_REVIEW_TYPE},
        )
        # A retried job leaves one run per attempt; only its final run counts.
        runs = [
            self._run_summary(row)
            for row in result
            if not row.final_run_id or row.final_run_id == str(row.workflow_run_id)
        ]
        return [run for run in runs if run["review_reasons"]]

    async def run_detail(self, *, workspace_id: UUID, run_id: UUID) -> dict:
        result = await self.db.execute(
            text(self._RUNS_SQL + " AND r.workflow_run_id = :run_id"),
            {"workspace_id": workspace_id, "run_id": run_id, "flag_type": RUN_FLAG_REVIEW_TYPE},
        )
        row = result.first()
        if row is None:
            raise HTTPException(status_code=404, detail="Run not found")

        workflow = (
            await self.db.execute(
                text("SELECT workflow FROM workflow_runs WHERE workflow_run_id = :id"),
                {"id": run_id},
            )
        ).scalar_one()
        events = (
            await self.db.execute(
                text(
                    """
                    SELECT event, created_at FROM workflow_run_events
                    WHERE workflow_run_id = :id ORDER BY id
                    """
                ),
                {"id": run_id},
            )
        ).all()

        steps: dict[str, dict] = {}
        for event, created_at in events:
            node_id = event.get("node_id")
            if not node_id:
                continue
            step = steps.setdefault(node_id, {"node_id": node_id, "status": "queued"})
            kind = event.get("event")
            if kind == "node_start":
                step.update(status="running", started_at=created_at)
            elif kind == "node_end":
                meta = event.get("meta") or {}
                step.update(
                    status="done",
                    ended_at=created_at,
                    output=_truncate(event.get("output")),
                    meta=meta,
                    problem=(
                        "handoff_required" if meta.get("handoff_required") else None
                    ),
                )
            elif kind == "node_skip":
                step.update(status="skipped", reason=event.get("reason"))
            elif kind == "node_error":
                step.update(
                    status="error",
                    ended_at=created_at,
                    error=_truncate(event.get("error") or event.get("message")),
                    problem="error",
                )
        for step in steps.values():
            if step.get("started_at") and step.get("ended_at"):
                step["duration_ms"] = round(
                    (step["ended_at"] - step["started_at"]).total_seconds() * 1000
                )

        likely_cause = next(
            (s["node_id"] for s in steps.values() if s.get("problem") == "error"),
            None,
        ) or next(
            (s["node_id"] for s in steps.values() if s.get("problem")),
            None,
        )
        if likely_cause is None and row.status == "failed":
            failed = ((row.extra or {}).get("failed_node") or {}).get("id")
            likely_cause = failed if failed in steps else None

        transcript = []
        if row.thread_id:
            messages = await self.db.execute(
                text(
                    """
                    SELECT m.id, m.sender_type, m.body, m.created_at
                    FROM cs_conversation_messages m
                    JOIN cs_conversations c ON c.id = m.conversation_id
                    WHERE m.conversation_id = :conversation_id AND c.user_id = :workspace_id
                    ORDER BY m.created_at
                    """
                ),
                {"conversation_id": row.thread_id, "workspace_id": workspace_id},
            )
            transcript = [
                {
                    "id": str(m.id),
                    "sender": str(m.sender_type.value if hasattr(m.sender_type, "value") else m.sender_type),
                    "body": m.body,
                    "created_at": m.created_at,
                }
                for m in messages
            ]

        flags = await self.db.execute(
            select(CustomerServiceQualityReview).where(
                CustomerServiceQualityReview.user_id == workspace_id,
                CustomerServiceQualityReview.review_type == RUN_FLAG_REVIEW_TYPE,
                CustomerServiceQualityReview.outcome == "open",
            )
        )
        run_flags = [
            {
                "id": str(flag.id),
                **(flag.issues or [{}])[0],
                "created_at": flag.created_at,
            }
            for flag in flags.scalars()
            if (flag.issues or [{}])[0].get("run_id") == str(run_id)
        ]

        return {
            **self._run_summary(row),
            "failure": (row.extra or {}).get("error"),
            "elapsed_sec": (row.extra or {}).get("elapsed_sec"),
            "graph": _graph_view(workflow, _catalog()),
            "steps": list(steps.values()),
            "likely_cause": likely_cause,
            "transcript": transcript,
            "flags": run_flags,
        }

    async def flag_run(
        self,
        *,
        workspace_id: UUID,
        reviewer_id: UUID,
        run_id: UUID,
        step_id: str | None,
        message_id: str | None,
        note: str,
    ) -> dict:
        run = await self.run_detail(workspace_id=workspace_id, run_id=run_id)
        if not run["conversation_id"]:
            raise HTTPException(status_code=409, detail="This run has no conversation to flag.")
        flag = CustomerServiceQualityReview(
            user_id=workspace_id,
            conversation_id=UUID(run["conversation_id"]),
            overall_score=0.0,
            issues=[
                {"run_id": str(run_id), "step_id": step_id, "message_id": message_id, "note": note}
            ],
            reviewer_type="human",
            reviewer_id=reviewer_id,
            review_type=RUN_FLAG_REVIEW_TYPE,
            outcome="open",
        )
        self.db.add(flag)
        await self.db.commit()
        return {"id": str(flag.id)}

    async def dismiss_run(self, *, workspace_id: UUID, reviewer_id: UUID, run_id: UUID) -> None:
        """"Not a problem": close open flags and keep the run out of the queue."""
        run = await self.run_detail(workspace_id=workspace_id, run_id=run_id)
        await self.db.execute(
            text(
                """
                UPDATE cs_quality_reviews SET outcome = 'dismissed'
                WHERE user_id = :workspace_id AND review_type = :flag_type
                  AND outcome = 'open' AND issues->0->>'run_id' = :run_id
                """
            ),
            {"workspace_id": workspace_id, "flag_type": RUN_FLAG_REVIEW_TYPE, "run_id": str(run_id)},
        )
        if run["conversation_id"] and not run["flags"]:
            self.db.add(
                CustomerServiceQualityReview(
                    user_id=workspace_id,
                    conversation_id=UUID(run["conversation_id"]),
                    overall_score=1.0,
                    issues=[{"run_id": str(run_id), "note": "Not a problem"}],
                    reviewer_type="human",
                    reviewer_id=reviewer_id,
                    review_type=RUN_FLAG_REVIEW_TYPE,
                    outcome="dismissed",
                )
            )
        await self.db.commit()
