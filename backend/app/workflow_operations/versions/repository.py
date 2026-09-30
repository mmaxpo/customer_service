from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _jsonb(value: Any) -> str:
    return json.dumps(jsonable_encoder(value), ensure_ascii=False)


class WorkflowVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_definition(
        self,
        *,
        user_id: UUID,
        name: str,
        slug: str,
        description: str | None,
        metadata_json: dict[str, Any],
    ) -> dict:
        q = text(
            """
            INSERT INTO workflow_definitions (
                id, user_id, name, slug, description, metadata_json
            )
            VALUES (
                :id, :user_id, :name, :slug, :description, CAST(:metadata_json AS jsonb)
            )
            RETURNING id, user_id, name, slug, description, latest_version,
                      active_version, metadata_json, created_at, updated_at
            """
        )

        res = await self.db.execute(
            q,
            {
                "id": uuid4(),
                "user_id": user_id,
                "name": name,
                "slug": slug,
                "description": description,
                "metadata_json": _jsonb(metadata_json or {}),
            },
        )
        await self.db.commit()
        return dict(res.mappings().one())

    async def get_definition(self, *, definition_id: UUID) -> dict | None:
        res = await self.db.execute(
            text(
                """
                SELECT id, user_id, name, slug, description, latest_version,
                       active_version, metadata_json, created_at, updated_at
                FROM workflow_definitions
                WHERE id = :definition_id
                """
            ),
            {"definition_id": definition_id},
        )
        row = res.mappings().first()
        return dict(row) if row else None

    async def list_definitions(self, *, user_id: UUID) -> list[dict]:
        res = await self.db.execute(
            text(
                """
                SELECT id, user_id, name, slug, description, latest_version,
                       active_version, metadata_json, created_at, updated_at
                FROM workflow_definitions
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [dict(row) for row in res.mappings().all()]

    async def create_version(
        self,
        *,
        definition_id: UUID,
        user_id: UUID,
        workflow_json: dict[str, Any],
        notes: str | None,
        evaluation_summary: dict[str, Any],
        metadata_json: dict[str, Any],
    ) -> dict:
        definition = await self.get_definition(definition_id=definition_id)
        if not definition:
            raise ValueError("workflow_definition_not_found")

        next_version = int(definition["latest_version"] or 0) + 1

        version_id = uuid4()

        await self.db.execute(
            text(
                """
                INSERT INTO workflow_versions (
                    id, workflow_definition_id, user_id, version,
                    workflow_json, status, notes, evaluation_summary, metadata_json
                )
                VALUES (
                    :id, :definition_id, :user_id, :version,
                    CAST(:workflow_json AS jsonb), 'draft', :notes,
                    CAST(:evaluation_summary AS jsonb),
                    CAST(:metadata_json AS jsonb)
                )
                """
            ),
            {
                "id": version_id,
                "definition_id": definition_id,
                "user_id": user_id,
                "version": next_version,
                "workflow_json": _jsonb(workflow_json),
                "notes": notes,
                "evaluation_summary": _jsonb(evaluation_summary or {}),
                "metadata_json": _jsonb(metadata_json or {}),
            },
        )

        await self.db.execute(
            text(
                """
                UPDATE workflow_definitions
                SET latest_version = :version,
                    updated_at = now()
                WHERE id = :definition_id
                """
            ),
            {
                "version": next_version,
                "definition_id": definition_id,
            },
        )

        await self.db.commit()

        version = await self.get_version(
            definition_id=definition_id,
            version=next_version,
        )
        assert version is not None
        return version

    async def get_version(
        self,
        *,
        definition_id: UUID,
        version: int,
    ) -> dict | None:
        res = await self.db.execute(
            text(
                """
                SELECT id, workflow_definition_id, user_id, version, workflow_json,
                       status, notes, evaluation_summary, metadata_json,
                       created_at, published_at
                FROM workflow_versions
                WHERE workflow_definition_id = :definition_id
                  AND version = :version
                """
            ),
            {
                "definition_id": definition_id,
                "version": version,
            },
        )
        row = res.mappings().first()
        return dict(row) if row else None

    async def list_versions(self, *, definition_id: UUID) -> list[dict]:
        res = await self.db.execute(
            text(
                """
                SELECT id, workflow_definition_id, user_id, version, workflow_json,
                       status, notes, evaluation_summary, metadata_json,
                       created_at, published_at
                FROM workflow_versions
                WHERE workflow_definition_id = :definition_id
                ORDER BY version DESC
                """
            ),
            {"definition_id": definition_id},
        )
        return [dict(row) for row in res.mappings().all()]

    async def publish_version(
        self,
        *,
        definition_id: UUID,
        version: int,
    ) -> dict:
        target = await self.get_version(
            definition_id=definition_id,
            version=version,
        )
        if not target:
            raise ValueError("workflow_version_not_found")

        await self.db.execute(
            text(
                """
                UPDATE workflow_versions
                SET status = 'archived'
                WHERE workflow_definition_id = :definition_id
                  AND status = 'published'
                """
            ),
            {"definition_id": definition_id},
        )

        await self.db.execute(
            text(
                """
                UPDATE workflow_versions
                SET status = 'published',
                    published_at = now()
                WHERE workflow_definition_id = :definition_id
                  AND version = :version
                """
            ),
            {
                "definition_id": definition_id,
                "version": version,
            },
        )

        await self.db.execute(
            text(
                """
                UPDATE workflow_definitions
                SET active_version = :version,
                    updated_at = now()
                WHERE id = :definition_id
                """
            ),
            {
                "definition_id": definition_id,
                "version": version,
            },
        )

        await self.db.commit()

        published = await self.get_version(
            definition_id=definition_id,
            version=version,
        )
        assert published is not None
        return published

    async def get_active_version(self, *, definition_id: UUID) -> dict | None:
        definition = await self.get_definition(definition_id=definition_id)
        if not definition or definition.get("active_version") is None:
            return None

        return await self.get_version(
            definition_id=definition_id,
            version=int(definition["active_version"]),
        )
