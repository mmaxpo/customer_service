from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/knowledge.py
# ============================================================
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.knowledge import (
    CustomerServiceKnowledgeContext,
    CustomerServiceKnowledgeSearchRequest,
    KnowledgeEvaluationQuestionCreate,
    KnowledgeEvaluationQuestionRead,
    KnowledgeInlineIngestRequest,
    KnowledgeSettingsRead,
    KnowledgeSettingsUpdate,
    KnowledgeSourceRead,
    KnowledgeURLIngestRequest,
)
from app.domains.customer_service.services.knowledge import (
    CustomerServiceKnowledgeService,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.tenancy.context import Principal, get_current_principal

knowledge_router = APIRouter(tags=["Customer Service - Knowledge"])


@knowledge_router.post(
    "/knowledge/search",
    response_model=CustomerServiceKnowledgeContext,
)
async def search_knowledge(
    payload: CustomerServiceKnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceKnowledgeService(db).search_context(
        user_id=current_user.id,
        query=payload.query,
        k=payload.k,
    )


def _require_admin(principal: Principal) -> None:
    if principal.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")


@knowledge_router.get("/knowledge/sources", response_model=list[KnowledgeSourceRead])
async def list_knowledge_sources(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    return await CustomerServiceKnowledgeService(db).list_sources(
        workspace_id=principal.workspace_id
    )


@knowledge_router.post("/knowledge/sources/inline", response_model=KnowledgeSourceRead)
async def ingest_inline_source(
    payload: KnowledgeInlineIngestRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceKnowledgeService(db).ingest_inline(
        workspace_id=principal.workspace_id,
        actor_user_id=principal.user_id,
        name=payload.name,
        text=payload.text,
    )


@knowledge_router.post("/knowledge/sources/url", response_model=KnowledgeSourceRead)
async def ingest_url_source(
    payload: KnowledgeURLIngestRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceKnowledgeService(db).ingest_url(
        workspace_id=principal.workspace_id,
        actor_user_id=principal.user_id,
        url=payload.url,
        name=payload.name,
        max_pages=payload.max_pages,
    )


@knowledge_router.post("/knowledge/sources/file", response_model=KnowledgeSourceRead)
async def ingest_file_source(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    data = await file.read(15 * 1024 * 1024 + 1)
    return await CustomerServiceKnowledgeService(db).ingest_file(
        workspace_id=principal.workspace_id,
        actor_user_id=principal.user_id,
        filename=file.filename or "knowledge-file",
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )


@knowledge_router.post(
    "/knowledge/sources/shopify-sync", response_model=list[KnowledgeSourceRead]
)
async def sync_shopify_knowledge(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceKnowledgeService(db).sync_shopify(
        workspace_id=principal.workspace_id,
        actor_user_id=principal.user_id,
    )


@knowledge_router.post(
    "/knowledge/sources/{source_id}/reindex", response_model=KnowledgeSourceRead
)
async def reindex_knowledge_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceKnowledgeService(db).reindex(
        workspace_id=principal.workspace_id, source_id=source_id
    )


@knowledge_router.delete("/knowledge/sources/{source_id}", status_code=204)
async def delete_knowledge_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    await CustomerServiceKnowledgeService(db).delete_source(
        workspace_id=principal.workspace_id, source_id=source_id
    )


@knowledge_router.get("/knowledge/settings", response_model=KnowledgeSettingsRead)
async def get_knowledge_settings(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    return await CustomerServiceKnowledgeService(db).get_settings(
        workspace_id=principal.workspace_id
    )


@knowledge_router.put("/knowledge/settings", response_model=KnowledgeSettingsRead)
async def update_knowledge_settings(
    payload: KnowledgeSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceKnowledgeService(db).update_settings(
        workspace_id=principal.workspace_id, payload=payload
    )


@knowledge_router.get(
    "/knowledge/evaluations", response_model=list[KnowledgeEvaluationQuestionRead]
)
async def list_knowledge_evaluations(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    return await CustomerServiceKnowledgeService(db).list_evaluations(
        workspace_id=principal.workspace_id
    )


@knowledge_router.post(
    "/knowledge/evaluations", response_model=KnowledgeEvaluationQuestionRead
)
async def create_knowledge_evaluation(
    payload: KnowledgeEvaluationQuestionCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceKnowledgeService(db).create_evaluation(
        workspace_id=principal.workspace_id, payload=payload
    )


@knowledge_router.post("/knowledge/evaluations/run")
async def run_knowledge_evaluations(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceKnowledgeService(db).run_evaluations(
        workspace_id=principal.workspace_id
    )


__all__ = [
    "knowledge_router",
]
