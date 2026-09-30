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
from app.runtime.engine.validator import validate_workflow
from app.runtime.nodes.registry.core import list_registered_nodes
from app.workflow_operations.versions.repository import WorkflowVersionRepository

RUN_FLAG_REVIEW_TYPE = "run_flag"
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
                "type_title": entry.get("title") or node_type,
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
            errors.append(f'"{_humanize(node_id)}" uses a step type this workspace does not have ({node_type}).')
            continue
        if _needs_approval(node_type, entry) and not has_approval_before(node_id, set()):
            errors.append(f'"{_humanize(node_id)}" changes customer or order data and needs an approval step before it.')
    return errors


def _edit_summary(base: dict, proposed: dict, catalog: dict[str, dict]) -> list[dict]:
    diff = _diff(base, proposed)
    nodes = {str(n.get("id")): n for n in proposed.get("nodes") or []}
    removed_nodes = {str(n.get("id")): n for n in base.get("nodes") or []}

    def name(node: dict) -> str:
        return (node.get("data") or {}).get("label") or _humanize(str(node.get("id")))

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
                    "description": template.description if template else None,
                    "enabled": subscription.is_active,
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
                f' config keys: {sorted((e.get("schema") or {}).get("properties", {}).keys())}'
                if t in used or e.get("category") in {"logic", "control"}
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
                    metadata_json = CAST(:meta AS jsonb)
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
                 j.payload->'extras'->'workflow_version' AS version
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
        runs = [self._run_summary(row) for row in result]
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
