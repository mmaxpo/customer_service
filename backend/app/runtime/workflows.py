"""
Public Runtime saved-workflow boundary.

Application adapters depend on the generic RuntimeWorkflowRepository contract.
Runtime owns selection and construction of the concrete persistence adapter.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.engine.workflow_repo_postgres import (
    PostgresWorkflowRepo,
)


class RuntimeWorkflowRepository(Protocol):
    """Persistence contract for user-owned saved Runtime workflows."""

    async def create(
        self,
        *,
        user_id: UUID,
        name: str,
        workflow: dict[str, Any],
    ) -> dict[str, Any]: ...

    async def get(
        self,
        *,
        user_id: UUID,
        workflow_id: UUID,
    ) -> dict[str, Any] | None: ...

    async def list(
        self,
        *,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    async def update(
        self,
        *,
        user_id: UUID,
        workflow_id: UUID,
        name: str,
        workflow: dict[str, Any],
    ) -> bool: ...

    async def delete(
        self,
        *,
        user_id: UUID,
        workflow_id: UUID,
    ) -> bool: ...


def build_runtime_workflow_repository(
    db: AsyncSession,
) -> RuntimeWorkflowRepository:
    """
    Build the installed repository for durable saved Runtime workflows.

    Concrete PostgreSQL ownership remains inside Runtime.
    """

    return PostgresWorkflowRepo(db)


__all__ = [
    "RuntimeWorkflowRepository",
    "build_runtime_workflow_repository",
]
