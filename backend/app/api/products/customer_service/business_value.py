from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.business_value import (
    BusinessValueAnalyticsRead,
)
from app.domains.customer_service.security.rbac import (
    require_customer_service_permission,
)
from app.domains.customer_service.services.business_value_analytics import (
    CustomerServiceBusinessValueAnalyticsService,
)


business_value_router = APIRouter(tags=["Customer Service - Business Value"])


@business_value_router.get(
    "/analytics/business-value", response_model=BusinessValueAnalyticsRead
)
async def business_value_analytics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    principal=Depends(require_customer_service_permission("cs.analytics.read")),
):
    return await CustomerServiceBusinessValueAnalyticsService(db).report(
        workspace_id=principal.id, days=days
    )


__all__ = ["business_value_router"]
