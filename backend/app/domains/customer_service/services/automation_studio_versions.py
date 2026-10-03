"""Automation studio versions job methods."""

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
    catalog,
    diff,
    edit_summary,
    graph_view,
    humanize,
    needs_approval,
    node_type,
    step_name,
    truncate,
    validate,
)
from .automation_studio_json import parse_json


class VersionsStudioMixin:
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
