"""Automation studio testing job methods."""

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

DRY_RUN_BLOCKED = {"capability.invoke", "agent.custom", "agent.langgraph", "agent.mcp", "subworkflow.call", "wait.time", "wait.event", "human.approval"}


class TestingStudioMixin:
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
            if get_node_type(node) in DRY_RUN_BLOCKED:
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
                or humanize(item["node_id"])
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
                    "draft_error": truncate(outcome["error"]),
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
