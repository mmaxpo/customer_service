from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow_operations.metrics.repository import WorkflowMetricsRepository


class WorkflowMetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkflowMetricsRepository(db)

    async def record_from_workflow_result(
        self,
        *,
        user_id: UUID,
        result: dict[str, Any],
        workflow_definition_id: UUID | None = None,
        workflow_version: int | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict:
        meta = result.get("meta") or {}
        final_state = meta.get("final_state") or {}

        workflow_run_id = (
            meta.get("workflow_run_id")
            or final_state.get("workflow_run_id")
            or result.get("workflow_run_id")
        )

        events = meta.get("events") or final_state.get("meta", {}).get("events") or []
        status = meta.get("status") or final_state.get("status") or "unknown"

        node_count = sum(1 for event in events if event.get("event") == "node_end")
        retry_count = sum(1 for event in events if event.get("event") == "node_retry")
        approval_count = sum(
            1
            for event in events
            if event.get("event") in {"wait_created", "run_paused"}
            and (
                event.get("wait_type") == "approval"
                or (event.get("interrupt") or {}).get("kind") == "approval"
            )
        )

        errors = final_state.get("errors") or {}
        error_count = len(errors)

        duration_ms = meta.get("elapsed_ms")
        if duration_ms is None and meta.get("elapsed_sec") is not None:
            duration_ms = int(float(meta["elapsed_sec"]) * 1000)

        return await self.repo.record_run_metric(
            user_id=user_id,
            workflow_run_id=UUID(str(workflow_run_id)) if workflow_run_id else None,
            workflow_definition_id=workflow_definition_id,
            workflow_version=workflow_version,
            status=str(status),
            duration_ms=int(duration_ms) if duration_ms is not None else None,
            node_count=node_count,
            error_count=error_count,
            retry_count=retry_count,
            approval_count=approval_count,
            metadata_json=metadata_json or {},
        )

    async def summarize_version(
        self,
        *,
        user_id: UUID,
        workflow_definition_id: UUID,
        workflow_version: int,
    ) -> dict:
        return await self.repo.summarize_version(
            user_id=user_id,
            workflow_definition_id=workflow_definition_id,
            workflow_version=workflow_version,
        )
