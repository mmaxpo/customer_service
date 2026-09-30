from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.email_identity import (
    EmailIdentityRead,
    EmailIdentityUpdate,
)
from app.domains.customer_service.services.email_identity import (
    CustomerServiceEmailIdentityService,
)
from app.tenancy.context import Principal, get_current_principal


email_identity_router = APIRouter(tags=["Customer Service - Email Identity"])


def _require_admin(principal: Principal) -> None:
    if principal.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")


@email_identity_router.get("/email/identity", response_model=EmailIdentityRead | None)
async def get_email_identity(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    return await CustomerServiceEmailIdentityService(db).get(
        workspace_id=principal.workspace_id
    )


@email_identity_router.put("/email/identity", response_model=EmailIdentityRead)
async def configure_email_identity(
    payload: EmailIdentityUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceEmailIdentityService(db).configure(
        workspace_id=principal.workspace_id,
        payload=payload,
    )


@email_identity_router.post("/email/identity/verify", response_model=EmailIdentityRead)
async def verify_email_identity(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_admin(principal)
    return await CustomerServiceEmailIdentityService(db).verify(
        workspace_id=principal.workspace_id
    )
