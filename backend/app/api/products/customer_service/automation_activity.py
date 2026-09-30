from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.automation_activity import (
    AutomationActivityCategory,
    AutomationActivityRead,
)
from app.domains.customer_service.security.rbac import get_customer_service_principal
from app.domains.customer_service.services.automation_activity import (
    CustomerServiceAutomationActivityService,
)


automation_activity_router = APIRouter(tags=["Customer Service - Automation Activity"])


@automation_activity_router.get(
    "/conversations/{conversation_id}/automation-activity",
    response_model=AutomationActivityRead,
)
async def list_automation_activity(
    conversation_id: UUID,
    category: list[AutomationActivityCategory] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: AsyncSession = Depends(get_db),
    principal=Depends(get_customer_service_principal),
):
    return await CustomerServiceAutomationActivityService(db).list(
        workspace_id=principal.id,
        conversation_id=conversation_id,
        categories=set(category) if category else None,
        limit=limit,
    )


__all__ = ["automation_activity_router"]
