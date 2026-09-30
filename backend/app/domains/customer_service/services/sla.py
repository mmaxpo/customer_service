from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    CustomerServiceNotification,
    CustomerServiceSLACalendar,
    SLAPolicy,
    SLATargetType,
)
from app.domains.customer_service.repositories.sla import SLARepository
from app.domains.customer_service.realtime.publisher import (
    CustomerServiceRealtimePublisher,
)
from app.domains.customer_service.models import Ticket
from app.domains.customer_service.services.notifications import NotificationService
from app.tenancy.models import Workspace
from app.tenancy.working_calendar import add_working_minutes, resolved_workspace_calendar


def add_business_minutes(
    start_at: datetime, minutes: int, business_hours: dict | None
) -> datetime:
    """
    Add SLA minutes using optional business-hour windows.

    business_hours shape:
    {
      "timezone": "UTC",
      "weekly_hours": {
        "mon": [{"start": "09:00", "end": "17:00"}],
        "tue": [{"start": "09:00", "end": "17:00"}]
      }
    }

    Missing business_hours keeps old 24/7 behavior.
    """
    try:
        return add_working_minutes(start_at, minutes, business_hours)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class SLAService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SLARepository(db)

    async def create_policy(self, *, user_id, payload):
        if payload.calendar_id is not None:
            calendar = await self.db.scalar(
                select(CustomerServiceSLACalendar).where(
                    CustomerServiceSLACalendar.id == payload.calendar_id,
                    CustomerServiceSLACalendar.workspace_id == user_id,
                )
            )
            if calendar is None:
                raise HTTPException(status_code=404, detail="SLA calendar not found")
        return await self.repo.create_policy(user_id=user_id, payload=payload)

    async def list_policies(self, *, user_id):
        return await self.repo.list_policies(user_id=user_id)

    async def list_violations(self, *, user_id, status: str | None = None):
        return await self.repo.list_violations(user_id=user_id, status=status)

    async def create_targets_for_ticket(self, *, ticket):
        policy = await self.repo.get_active_policy_for_priority(
            user_id=ticket.user_id,
            priority=ticket.priority,
        )

        if policy is None:
            return []

        business_hours = policy.business_hours
        if policy.calendar_id is not None:
            calendar = await self.db.scalar(
                select(CustomerServiceSLACalendar).where(
                    CustomerServiceSLACalendar.id == policy.calendar_id,
                    CustomerServiceSLACalendar.workspace_id == ticket.user_id,
                )
            )
            if calendar is not None:
                business_hours = {
                    "timezone": calendar.timezone,
                    "weekly_hours": {
                        day: [
                            {"start": window[0], "end": window[1]}
                            for window in windows
                        ]
                        for day, windows in (calendar.weekly_hours or {}).items()
                    },
                    "holidays": calendar.holidays or [],
                    "escalation_policy": calendar.escalation_policy or {},
                }
        elif business_hours is None:
            workspace = await self.db.get(Workspace, ticket.user_id)
            if workspace is not None:
                business_hours = resolved_workspace_calendar(
                    timezone_name=workspace.timezone,
                    business_hours=workspace.business_hours,
                )

        created_at = ticket.created_at

        targets = [
            await self.repo.create_violation_target(
                user_id=ticket.user_id,
                ticket_id=ticket.id,
                policy_id=policy.id,
                target_type=SLATargetType.FIRST_RESPONSE,
                due_at=add_business_minutes(
                    created_at, policy.first_response_minutes, business_hours
                ),
            ),
            await self.repo.create_violation_target(
                user_id=ticket.user_id,
                ticket_id=ticket.id,
                policy_id=policy.id,
                target_type=SLATargetType.RESOLUTION,
                due_at=add_business_minutes(
                    created_at, policy.resolution_minutes, business_hours
                ),
            ),
        ]

        await self.db.commit()

        for target in targets:
            await self.db.refresh(target)
            await CustomerServiceRealtimePublisher().publish_sla_updated(
                user_id=target.user_id,
                ticket_id=target.ticket_id,
                status="target_created",
                payload={
                    "sla_violation_id": str(target.id),
                    "target_type": str(target.target_type),
                    "due_at": target.due_at.isoformat() if target.due_at else None,
                },
            )
        return targets

    async def check_at_risk(self, *, user_id, now: datetime | None = None):
        """Notify assignees once when a calendar's pre-breach threshold is reached."""
        now = now or datetime.now().astimezone()
        targets = await self.repo.list_open_targets(user_id=user_id)
        at_risk = []
        for target in targets:
            policy = await self.db.get(SLAPolicy, target.policy_id)
            threshold = 30
            if policy and policy.calendar_id:
                calendar = await self.db.get(CustomerServiceSLACalendar, policy.calendar_id)
                threshold = int(
                    (calendar.escalation_policy or {}).get("before_breach_minutes", 30)
                )
            if target.due_at > now + timedelta(minutes=max(0, threshold)):
                continue
            ticket = await self.db.get(Ticket, target.ticket_id)
            if not ticket or not ticket.assigned_to:
                continue
            existing = await self.db.scalar(
                select(CustomerServiceNotification.id).where(
                    CustomerServiceNotification.workspace_id == user_id,
                    CustomerServiceNotification.kind == "sla_risk",
                    CustomerServiceNotification.entity_id == ticket.id,
                    CustomerServiceNotification.read_at.is_(None),
                )
            )
            if existing is None:
                await NotificationService(self.db).create_if_uuid(
                    workspace_id=user_id,
                    recipient_user_id=ticket.assigned_to,
                    kind="sla_risk",
                    entity_type="ticket",
                    entity_id=ticket.id,
                    payload={
                        "state": "at_risk",
                        "target_type": str(target.target_type),
                        "due_at": target.due_at.isoformat(),
                    },
                )
            at_risk.append(target)
        return at_risk

    async def check_breaches(self, *, user_id):
        due_targets = await self.repo.list_open_due_targets(
            user_id=user_id,
        )
        breached = []

        for target in due_targets:
            breached_target = await self.repo.mark_breached(target)
            breached.append(breached_target)
            await CustomerServiceRealtimePublisher().publish_sla_updated(
                user_id=breached_target.user_id,
                ticket_id=breached_target.ticket_id,
                status="breached",
                payload={
                    "sla_violation_id": str(breached_target.id),
                    "target_type": str(breached_target.target_type),
                    "due_at": breached_target.due_at.isoformat()
                    if breached_target.due_at
                    else None,
                    "breached_at": breached_target.breached_at.isoformat()
                    if breached_target.breached_at
                    else None,
                },
            )
            ticket = await self.db.get(Ticket, breached_target.ticket_id)
            if ticket and ticket.assigned_to:
                await NotificationService(self.db).create_if_uuid(
                    workspace_id=breached_target.user_id,
                    recipient_user_id=ticket.assigned_to,
                    kind="sla_risk",
                    entity_type="ticket",
                    entity_id=ticket.id,
                    payload={
                        "state": "breached",
                        "target_type": str(breached_target.target_type),
                    },
                )

        return breached

    async def resolve_first_response_targets(self, *, ticket_id):
        resolved = await self.repo.resolve_targets(
            ticket_id=ticket_id,
            target_type=SLATargetType.FIRST_RESPONSE,
        )

        for target in resolved:
            await CustomerServiceRealtimePublisher().publish_sla_updated(
                user_id=target.user_id,
                ticket_id=target.ticket_id,
                status="first_response_resolved",
                payload={
                    "sla_violation_id": str(target.id),
                    "target_type": str(target.target_type),
                    "resolved_at": getattr(target, "resolved_at", None).isoformat()
                    if getattr(target, "resolved_at", None)
                    else (
                        target.updated_at.isoformat()
                        if getattr(target, "updated_at", None)
                        else None
                    ),
                },
            )

        return resolved

    async def resolve_resolution_targets(self, *, ticket_id):
        resolved = await self.repo.resolve_targets(
            ticket_id=ticket_id,
            target_type=SLATargetType.RESOLUTION,
        )

        for target in resolved:
            await CustomerServiceRealtimePublisher().publish_sla_updated(
                user_id=target.user_id,
                ticket_id=target.ticket_id,
                status="resolution_resolved",
                payload={
                    "sla_violation_id": str(target.id),
                    "target_type": str(target.target_type),
                    "resolved_at": getattr(target, "resolved_at", None).isoformat()
                    if getattr(target, "resolved_at", None)
                    else (
                        target.updated_at.isoformat()
                        if getattr(target, "updated_at", None)
                        else None
                    ),
                },
            )

        return resolved
