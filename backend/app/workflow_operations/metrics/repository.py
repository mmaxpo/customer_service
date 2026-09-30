from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _jsonb(value: Any) -> str:
    return json.dumps(jsonable_encoder(value), ensure_ascii=False)


class WorkflowMetricsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_run_metric(
        self,
        *,
        user_id: UUID,
        workflow_run_id: UUID | None,
        workflow_definition_id: UUID | None,
        workflow_version: int | None,
        status: str,
        duration_ms: int | None,
        node_count: int,
        error_count: int,
        retry_count: int,
        approval_count: int,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict:
        q = text(
            """
            INSERT INTO workflow_run_metrics (
                id, user_id, workflow_run_id, workflow_definition_id,
                workflow_version, status, duration_ms, node_count,
                error_count, retry_count, approval_count, metadata_json
            )
            VALUES (
                :id, :user_id, :workflow_run_id, :workflow_definition_id,
                :workflow_version, :status, :duration_ms, :node_count,
                :error_count, :retry_count, :approval_count,
                CAST(:metadata_json AS jsonb)
            )
            RETURNING id, user_id, workflow_run_id, workflow_definition_id,
                      workflow_version, status, duration_ms, node_count,
                      error_count, retry_count, approval_count, metadata_json,
                      created_at
            """
        )

        res = await self.db.execute(
            q,
            {
                "id": uuid4(),
                "user_id": user_id,
                "workflow_run_id": workflow_run_id,
                "workflow_definition_id": workflow_definition_id,
                "workflow_version": workflow_version,
                "status": status,
                "duration_ms": duration_ms,
                "node_count": node_count,
                "error_count": error_count,
                "retry_count": retry_count,
                "approval_count": approval_count,
                "metadata_json": _jsonb(metadata_json or {}),
            },
        )
        await self.db.commit()
        return dict(res.mappings().one())

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 100,
    ) -> list[dict]:
        res = await self.db.execute(
            text(
                """
                SELECT id, user_id, workflow_run_id, workflow_definition_id,
                       workflow_version, status, duration_ms, node_count,
                       error_count, retry_count, approval_count, metadata_json,
                       created_at
                FROM workflow_run_metrics
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "limit": limit},
        )
        return [dict(row) for row in res.mappings().all()]

    async def summarize_version(
        self,
        *,
        user_id: UUID,
        workflow_definition_id: UUID,
        workflow_version: int,
    ) -> dict:
        res = await self.db.execute(
            text(
                """
                SELECT
                    COUNT(*)::int AS run_count,
                    COALESCE(SUM(CASE WHEN status IN ('ok', 'done', 'succeeded') THEN 1 ELSE 0 END), 0)::int AS success_count,
                    COALESCE(SUM(CASE WHEN status NOT IN ('ok', 'done', 'succeeded') THEN 1 ELSE 0 END), 0)::int AS failure_count,
                    COALESCE(AVG(duration_ms), 0)::float AS avg_duration_ms,
                    COALESCE(SUM(error_count), 0)::int AS total_errors,
                    COALESCE(SUM(retry_count), 0)::int AS total_retries,
                    COALESCE(SUM(approval_count), 0)::int AS total_approvals
                FROM workflow_run_metrics
                WHERE user_id = :user_id
                  AND workflow_definition_id = :workflow_definition_id
                  AND workflow_version = :workflow_version
                """
            ),
            {
                "user_id": user_id,
                "workflow_definition_id": workflow_definition_id,
                "workflow_version": workflow_version,
            },
        )

        row = dict(res.mappings().one())
        run_count = int(row["run_count"] or 0)
        success_count = int(row["success_count"] or 0)

        row["success_rate"] = success_count / run_count if run_count else 0.0
        row["workflow_definition_id"] = str(workflow_definition_id)
        row["workflow_version"] = workflow_version

        return row
