from fastapi import APIRouter, Depends

from app.domains.customer_service.product import customer_service_product_contract
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal,
)


product_router = APIRouter(tags=["Customer Service - Product"])


@product_router.get("/product")
async def get_product_contract(
    _principal=Depends(get_customer_service_principal),
):
    return customer_service_product_contract()
