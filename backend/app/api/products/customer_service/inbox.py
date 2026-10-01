from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/inbox.py
# ============================================================
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.services.collaboration import CollaborationService
from app.domains.customer_service.inbox.schemas import (
    InboundEmailIngestResult,
    NormalizedInboundEmail,
)
from app.domains.customer_service.inbox.service import InboundEmailIngestService
from app.domains.customer_service.schemas.inbox import InboxItem
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    require_customer_service_permission,
)
from app.domains.customer_service.services.inbox import InboxService
from app.domains.customer_service.services.messaging import CustomerServiceMessagingService
from uuid import UUID
from fastapi import HTTPException
from app.domains.customer_service.repositories.tickets import TicketRepository
from app.domains.customer_service.schemas.routing import (
    AutoAssignRequest,
    AutoAssignResult,
)
from app.domains.customer_service.schemas.tickets import TicketRead, TicketUpdate
from app.domains.customer_service.services.assignment import AssignmentService
from app.domains.customer_service.services.routing import CustomerServiceRoutingService
from app.domains.customer_service.schemas.shipping import (
    ShippingTrackingRead,
    ShippingTrackRequest,
)
from app.domains.customer_service.services.shipping import ShippingService

inbox_router = APIRouter(tags=["Customer Service - Inbox"])


@inbox_router.get("/", response_model=list[InboxItem])
async def get_inbox(
    folder: Literal["inbox", "snoozed", "spam", "all"] = "inbox",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.inbox.read")),
):
    return await InboxService(db).get_inbox(
        current_user.id,
        folder=folder,
        limit=limit,
        offset=offset,
    )


@inbox_router.post("/email/ingest", response_model=InboundEmailIngestResult)
async def ingest_email(
    payload: NormalizedInboundEmail,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await InboundEmailIngestService(db).ingest(
        user_id=current_user.id,
        email=payload,
    )


@inbox_router.post("/email/webhooks/resend/{workspace_id}")
async def ingest_resend_email_webhook(
    workspace_id: UUID,
    request: Request,
    svix_id: str = Header(alias="svix-id"),
    svix_timestamp: str = Header(alias="svix-timestamp"),
    svix_signature: str = Header(alias="svix-signature"),
    db: AsyncSession = Depends(get_db),
):
    return await CustomerServiceMessagingService(db).ingest_resend_webhook(
        workspace_id=workspace_id,
        raw_body=await request.body(),
        svix_id=svix_id,
        svix_timestamp=svix_timestamp,
        svix_signature=svix_signature,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/tickets.py
# ============================================================




tickets_router = APIRouter(tags=["Customer Service - Tickets"])


@tickets_router.get("/", response_model=list[TicketRead])
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.inbox.read")),
):
    return await TicketRepository(db).list(current_user.id)


@tickets_router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.inbox.read")),
):
    ticket = await TicketRepository(db).get(current_user.id, ticket_id)

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@tickets_router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    repository = TicketRepository(db)
    before = await repository.get(current_user.id, ticket_id)
    previous_assignee = before.assigned_to if before is not None else None
    ticket = await repository.update(
        current_user.id,
        ticket_id,
        payload,
    )

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if payload.assigned_to and payload.assigned_to != previous_assignee:
        await CollaborationService(db).notify_assignment(
            workspace_id=current_user.id,
            actor_id=getattr(current_user, "actor_user_id", current_user.id),
            conversation_id=ticket.conversation_id,
            assignee=payload.assigned_to,
        )
        await db.refresh(ticket)

    return ticket


@tickets_router.post("/{ticket_id}/close", response_model=TicketRead)
async def close_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.tickets.resolve")),
):
    ticket = await TicketRepository(db).update(
        current_user.id,
        ticket_id,
        TicketUpdate(status="closed"),
    )

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@tickets_router.post("/{ticket_id}/reopen", response_model=TicketRead)
async def reopen_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.tickets.resolve")),
):
    ticket = await TicketRepository(db).update(
        current_user.id,
        ticket_id,
        TicketUpdate(status="open"),
    )

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@tickets_router.post("/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: UUID,
    assigned_to: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_customer_service_permission("cs.tickets.assign")),
):
    assignment = await AssignmentService(
        db=db,
        user_id=current_user.id,
    ).assign(
        ticket_id=ticket_id,
        assigned_to=assigned_to,
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return assignment


@tickets_router.post("/{ticket_id}/auto-assign", response_model=AutoAssignResult)
async def auto_assign_ticket(
    ticket_id: UUID,
    payload: AutoAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceRoutingService(db).auto_assign_ticket(
        user_id=current_user.id,
        ticket_id=ticket_id,
        payload=payload,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/shipping.py
# ============================================================



shipping_router = APIRouter(tags=["Customer Service - Shipping"])


@shipping_router.post(
    "/shipping/track",
    response_model=ShippingTrackingRead,
)
async def track_shipping(
    payload: ShippingTrackRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ShippingService(db).track(
        user_id=current_user.id,
        tracking_number=payload.tracking_number,
        provider=payload.provider,
    )


__all__ = [
    "inbox_router",
    "tickets_router",
    "shipping_router",
]
