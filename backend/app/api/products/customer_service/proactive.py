from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.proactive import (
    ProactiveIncidentRead,
    ProactivePolicyRead,
    ProactivePolicyWrite,
)
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.proactive_playbooks import (
    CustomerServiceProactivePlaybookService,
)


proactive_router = APIRouter(tags=["Customer Service - Proactive Playbooks"])


def _service(db, principal):
    return CustomerServiceProactivePlaybookService(
        db, workspace_id=principal.workspace_id
    )


@proactive_router.post(
    "/proactive/policies/seed-defaults",
    response_model=list[ProactivePolicyRead],
)
async def seed_default_proactive_policies(
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, principal).seed_defaults()


@proactive_router.get(
    "/proactive/policies", response_model=list[ProactivePolicyRead]
)
async def list_proactive_policies(
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.analytics.read")),
):
    return await _service(db, principal).list_policies()


@proactive_router.put(
    "/proactive/policies/{signal}", response_model=ProactivePolicyRead
)
async def put_proactive_policy(
    signal: str,
    payload: ProactivePolicyWrite,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.settings.manage")),
):
    if payload.signal != signal:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="Path and payload signals differ")
    return await _service(db, principal).upsert(payload)


@proactive_router.post("/proactive/evaluate")
async def evaluate_proactive_playbooks(
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.settings.manage")),
):
    return await _service(db, principal).evaluate()


@proactive_router.get(
    "/proactive/incidents", response_model=list[ProactiveIncidentRead]
)
async def list_proactive_incidents(
    incident_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.analytics.read")),
):
    return await _service(db, principal).list_incidents(
        status=incident_status, limit=limit
    )


@proactive_router.post(
    "/proactive/incidents/{incident_id}/resolve",
    response_model=ProactiveIncidentRead,
)
async def resolve_proactive_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.conversations.reply")),
):
    return await _service(db, principal).resolve_incident(incident_id)


__all__ = ["proactive_router"]
