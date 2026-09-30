from __future__ import annotations

from typing import Any

from app.runtime.engine.context import RuntimeContext
from app.runtime.resources import (
    BusinessServices,
    RuntimeServiceFactory,
    RuntimeServices,
)


def _customer_service_shopify(db: Any) -> Any:
    """
    Resolve the installed Customer Service Shopify service lazily.

    Application composition can be imported before the complete domain
    model graph is initialized. Product implementation loading therefore
    happens only when Shopify behavior is actually used.
    """

    from app.domains.customer_service.services.shopify import (
        ShopifyService,
    )

    return ShopifyService(db)


class ShopifyRuntimeService:
    """
    Application-owned bridge between generic Runtime execution and the
    Customer Service Shopify implementation.

    Runtime Core depends only on the injected business service object.
    It does not import Shopify or Customer Service implementations.
    """

    def __init__(self, *, db: Any):
        self.db = db

    async def get_order(
        self,
        *,
        user_id: Any,
        order_ref: str,
        connection_id: Any | None = None,
    ) -> dict:
        kwargs = {"user_id": user_id, "order_ref": order_ref}
        if connection_id is not None:
            kwargs["connection_id"] = connection_id
        return await _customer_service_shopify(self.db).get_order(**kwargs)

    async def get_order_fresh(
        self,
        *,
        user_id: Any,
        order_ref: str,
        connection_id: Any | None = None,
    ) -> dict:
        kwargs = {"user_id": user_id, "order_ref": order_ref}
        if connection_id is not None:
            kwargs["connection_id"] = connection_id
        return await _customer_service_shopify(self.db).get_order_fresh(**kwargs)

    async def perform_order_action(
        self,
        *,
        user_id: Any,
        action: str,
        order_ref: str,
        connection_id: Any | None = None,
        reason: str | None = None,
        note: str | None = None,
        new_address: dict[str, Any] | None = None,
        amount: str | None = None,
        scope: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        approval_wait_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> dict:
        kwargs = {
            "user_id": user_id,
            "action": action,
            "order_ref": order_ref,
            "reason": reason,
            "note": note,
            "new_address": new_address,
            "amount": amount,
            "scope": scope,
            "idempotency_key": idempotency_key,
            "approval_wait_id": approval_wait_id,
            "workflow_run_id": workflow_run_id,
        }
        if connection_id is not None:
            kwargs["connection_id"] = connection_id
        return await _customer_service_shopify(self.db).perform_order_action(**kwargs)


def build_application_runtime_services(
    *,
    request: Any = None,
    db: Any = None,
    tools: Any = None,
    user_id: Any = None,
    tenant_id: Any = None,
    thread_id: Any = None,
    run_store: Any = None,
    event_sink: Any = None,
    extras: dict[str, Any] | None = None,
    capability_outcome_reporter: Any = None,
    provider_health_mode: Any = None,
) -> RuntimeServices:
    """
    Build Runtime services for this installed application.

    Application composition owns Product and Provider installation.
    Runtime Core receives only generic injected resources.
    """

    business = BusinessServices(
        shopify=(
            ShopifyRuntimeService(
                db=db,
            )
            if db is not None
            else None
        ),
    )

    return RuntimeServiceFactory.build(
        request=request,
        db=db,
        tools=tools,
        user_id=user_id,
        tenant_id=tenant_id,
        thread_id=thread_id,
        run_store=run_store,
        event_sink=event_sink,
        extras=extras,
        business=business,
        capability_outcome_reporter=(
            capability_outcome_reporter
        ),
        provider_health_mode=provider_health_mode,
    )


def build_application_runtime_context(
    *,
    request: Any,
    user_id: Any,
    thread_id: Any,
    db: Any,
    extras: dict[str, Any] | None = None,
    run_store: Any = None,
    event_sink: Any = None,
    workflow_run_id: Any = None,
) -> RuntimeContext:
    """
    Build the RuntimeContext used by this installed application.

    Application composition installs Product and Provider services first,
    then passes them into generic Runtime Core.
    """

    tools = getattr(
        getattr(request, "state", None),
        "tools",
        None,
    )

    services = build_application_runtime_services(
        request=request,
        db=db,
        tools=tools,
        user_id=user_id,
        thread_id=thread_id,
        run_store=run_store,
        event_sink=event_sink,
        extras=extras,
    )

    return RuntimeContext(
        request=request,
        user_id=user_id,
        thread_id=thread_id,
        db=db,
        extras=extras,
        run_store=run_store,
        event_sink=event_sink,
        workflow_run_id=workflow_run_id,
        services=services,
    )


__all__ = [
    "ShopifyRuntimeService",
    "build_application_runtime_context",
    "build_application_runtime_services",
]
