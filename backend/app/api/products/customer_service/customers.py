from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/customers.py
# ============================================================
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.customer_360 import Customer360Read
from app.domains.customer_service.schemas.customer_activity import (
    CustomerActivityEventRead,
)
from app.domains.customer_service.schemas.customer_risk import (
    CustomerRiskLeaderboardItem,
    CustomerRiskRead,
)
from app.domains.customer_service.schemas.customer_summary import (
    CustomerSummaryRead,
)
from app.domains.customer_service.schemas.customers import (
    CustomerCreate,
    CustomerRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    require_customer_service_permission,
)
from app.domains.customer_service.services.customer_360 import Customer360Service
from app.domains.customer_service.services.customer_activity import (
    CustomerActivityService,
)
from app.domains.customer_service.services.customer_risk import CustomerRiskService
from app.domains.customer_service.services.customers import CustomerService
from app.models.models import User

customers_router = APIRouter(tags=["Customer Service - Customers"])


@customers_router.post("/", response_model=CustomerRead)
async def create_customer(
    payload: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_customer_service_permission("cs.customers.manage")),
):
    try:
        return await CustomerService(db).create_customer(
            payload,
            current_user.id,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@customers_router.get("/", response_model=list[CustomerRead])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CustomerService(db).list_customers(
        current_user.id,
    )


@customers_router.get(
    "/{customer_id}/summary",
    response_model=CustomerSummaryRead,
)
async def get_customer_summary(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = await CustomerService(db).get_customer_summary(
        user_id=current_user.id,
        customer_id=customer_id,
    )

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return summary


@customers_router.get(
    "/{customer_id}/activity",
    response_model=list[CustomerActivityEventRead],
)
async def get_customer_activity(
    customer_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CustomerActivityService(db).list_activity(
        user_id=current_user.id,
        customer_id=customer_id,
        limit=limit,
    )


@customers_router.get(
    "/{customer_id}/360",
    response_model=Customer360Read,
)
async def get_customer_360(
    customer_id: UUID,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await Customer360Service(db).get_360(
        user_id=current_user.id,
        customer_id=customer_id,
        limit=limit,
    )


@customers_router.get(
    "/{customer_id}/risk",
    response_model=CustomerRiskRead,
)
async def get_customer_risk(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    risk = await CustomerRiskService(db).get_customer_risk(
        user_id=current_user.id,
        customer_id=customer_id,
    )

    if risk is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return risk


@customers_router.get(
    "/risk-leaderboard",
    response_model=list[CustomerRiskLeaderboardItem],
)
async def customer_risk_leaderboard(
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CustomerRiskService(db).leaderboard(
        user_id=current_user.id,
        limit=limit,
    )


__all__ = [
    "customers_router",
]
