"""Automation studio workflows job methods."""

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


class WorkflowsStudioMixin:
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
        catalog = get_catalog()
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
                    "graph": graph_view(self._live_graph(subscription, template), catalog),
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
        catalog = get_catalog()
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
                    "needs_approval": needs_approval(node_type, entry),
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
