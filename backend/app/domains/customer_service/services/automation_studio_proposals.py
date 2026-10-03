"""Automation studio proposals job methods."""

from __future__ import annotations

# The job mixins intentionally share the service module's dependency surface;
# keeping the moved methods verbatim is what makes this a behavior-only split.
# ruff: noqa: F401

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
from app.domains.customer_service.models.omnichannel import CustomerServiceEventSubscription
from app.domains.customer_service.models.quality import CustomerServiceQualityReview
from app.domains.customer_service.models.workflows import CustomerServiceWorkflowTemplate
from app.node_registration import register_application_nodes
from app.runtime.validation import validate_workflow
from app.runtime.nodes.registry.core import list_registered_nodes
from app.workflow_operations.versions.repository import WorkflowVersionRepository

from .automation_studio_helpers import (
    NODE_LIBRARY,
    catalog as get_catalog,
    diff,
    edit_summary,
    graph_view,
    humanize,
    needs_approval,
    node_type as get_node_type,
    step_name,
    truncate,
    validate,
)
from .automation_studio_json import parse_json


class ProposalsStudioMixin:
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
        used = {get_node_type(n) for n in base.get("nodes") or []}
        catalog_lines = [
            f'- {t}: {e.get("title")} ({e.get("category")}; risk {e.get("risk_level")}'
            + ("; needs a human.approval before it" if needs_approval(t, e) else "")
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
            parsed = parse_json(result.text)
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
        catalog = get_catalog()
        if workflow is not None:
            drafted = {"workflow": workflow, "summary": edit_summary(base, workflow, catalog)}
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
        catalog = get_catalog()
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
            "graph": graph_view(proposed, catalog),
            "base_graph": graph_view(base["workflow_json"] if base else {}, catalog),
            "diff": diff(base["workflow_json"] if base else {}, proposed),
            "validation_errors": validate(proposed, catalog),
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
            base=base["workflow_json"], requests=requests, catalog=get_catalog()
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
        errors = validate(row["workflow_json"], get_catalog())
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
