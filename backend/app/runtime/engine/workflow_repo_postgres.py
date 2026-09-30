from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def to_jsonb_str(obj: Any) -> str:
    safe = jsonable_encoder(obj)
    return json.dumps(safe, ensure_ascii=False)


class PostgresWorkflowRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, *, user_id: uuid.UUID, name: str, workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        wf_id = uuid.uuid4()
        q = text(
            """
            INSERT INTO runtime_workflows (id, user_id, name, workflow)
            VALUES (:id, :user_id, :name, CAST(:workflow AS jsonb))
            """
        )
        await self.db.execute(
            q,
            {
                "id": wf_id,
                "user_id": user_id,
                "name": name,
                "workflow": to_jsonb_str(workflow),
            },
        )
        await self.db.commit()
        return {"id": wf_id, "user_id": user_id, "name": name, "workflow": workflow}

    async def get(
        self, *, user_id: uuid.UUID, workflow_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        q = text(
            """
            SELECT id, user_id, name, workflow, created_at, updated_at
            FROM runtime_workflows
            WHERE id = :id AND user_id = :user_id
            """
        )
        res = await self.db.execute(q, {"id": workflow_id, "user_id": user_id})
        row = res.mappings().first()
        return dict(row) if row else None

    async def list(
        self, *, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        q = text(
            """
            SELECT id, name, created_at, updated_at
            FROM runtime_workflows
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        res = await self.db.execute(
            q, {"user_id": user_id, "limit": limit, "offset": offset}
        )
        return [dict(r) for r in res.mappings().all()]

    async def update(
        self,
        *,
        user_id: uuid.UUID,
        workflow_id: uuid.UUID,
        name: str,
        workflow: Dict[str, Any],
    ) -> bool:
        q = text(
            """
            UPDATE runtime_workflows
            SET name = :name,
                workflow = CAST(:workflow AS jsonb),
                updated_at = now()
            WHERE id = :id AND user_id = :user_id
            """
        )
        res = await self.db.execute(
            q,
            {
                "id": workflow_id,
                "user_id": user_id,
                "name": name,
                "workflow": to_jsonb_str(workflow),
            },
        )
        await self.db.commit()
        return (res.rowcount or 0) > 0

    async def delete(self, *, user_id: uuid.UUID, workflow_id: uuid.UUID) -> bool:
        q = text(
            """
            DELETE FROM runtime_workflows
            WHERE id = :id AND user_id = :user_id
            """
        )
        res = await self.db.execute(q, {"id": workflow_id, "user_id": user_id})
        await self.db.commit()
        return (res.rowcount or 0) > 0
