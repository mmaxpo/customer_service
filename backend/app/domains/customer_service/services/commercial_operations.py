from __future__ import annotations

import hashlib
import secrets
import subprocess
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.customer_service.models import (
    Conversation,
    ConversationFollower,
    ConversationEditLease,
    ConversationMessage,
    Customer,
    CustomerIdentity,
    CustomerServiceAttachment,
    CustomerServiceAuditLog,
    CustomerServiceCSATSurvey,
    CustomerServiceChannelConnection,
    CustomerServiceExternalConversationLink,
    CustomerServiceExternalMessageLink,
    CustomerServiceMergeEvent,
    CustomerServiceNotification,
    CustomerServiceOnboardingState,
    CustomerServicePrivacyRequest,
    CustomerServiceSavedView,
    CustomerServiceShopifyConnection,
    CustomerServiceSLACalendar,
    Ticket,
    WorkspaceSubscription,
)
from app.domains.customer_service.schemas.commercial import (
    ConversationSplitRequest,
    NotificationCreate,
    ResolutionRequest,
    SavedViewCreate,
    SLACalendarCreate,
    SubscriptionUpdate,
)
from app.domains.customer_service.services.attachment_storage import AttachmentStorage
from app.platform.jobs.service import JobService
from app.tenancy.models import WorkspaceMembership


DEFAULT_ENTITLEMENTS = {
    "agent_replies": True,
    "attachments": True,
    "saved_views": True,
    "monthly_conversations": 500,
    "members": 3,
}


class CommercialOperationsService:
    def __init__(self, db: AsyncSession, *, workspace_id: uuid.UUID, actor_id=None):
        self.db = db
        self.workspace_id = workspace_id
        self.actor_id = actor_id

    async def search_conversations(
        self,
        *,
        query: str | None,
        channel: str | None,
        status: str | None,
        assigned_to: str | None,
        unassigned: bool,
        limit: int,
        offset: int,
    ) -> list[dict]:
        statement = (
            select(Conversation, Customer, Ticket)
            .join(Customer, Customer.id == Conversation.customer_id)
            .outerjoin(Ticket, Ticket.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == self.workspace_id,
                Conversation.merged_into_id.is_(None),
            )
        )
        if query:
            pattern = f"%{query.strip()}%"
            message_match = (
                select(ConversationMessage.id)
                .where(
                    ConversationMessage.conversation_id == Conversation.id,
                    ConversationMessage.body.ilike(pattern),
                )
                .exists()
            )
            statement = statement.where(
                or_(
                    Conversation.subject.ilike(pattern),
                    Customer.name.ilike(pattern),
                    Customer.email.ilike(pattern),
                    message_match,
                )
            )
        if channel:
            statement = statement.where(Conversation.channel == channel)
        if status:
            statement = statement.where(Conversation.status == status)
        if assigned_to:
            statement = statement.where(Ticket.assigned_to == assigned_to)
        if unassigned:
            statement = statement.where(Ticket.assigned_to.is_(None))
        rows = (
            await self.db.execute(
                statement.order_by(Conversation.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return [
            {
                "conversation_id": str(conversation.id),
                "subject": conversation.subject,
                "channel": conversation.channel,
                "status": str(conversation.status),
                "customer": {
                    "id": str(customer.id),
                    "name": customer.name,
                    "email": customer.email,
                },
                "ticket": (
                    {
                        "id": str(ticket.id),
                        "status": str(ticket.status),
                        "priority": str(ticket.priority),
                        "assigned_to": ticket.assigned_to,
                    }
                    if ticket
                    else None
                ),
                "updated_at": conversation.updated_at,
            }
            for conversation, customer, ticket in rows
        ]

    async def create_saved_view(self, payload: SavedViewCreate):
        row = CustomerServiceSavedView(
            workspace_id=self.workspace_id,
            owner_user_id=self.actor_id,
            **payload.model_dump(),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list_saved_views(self):
        return list(
            await self.db.scalars(
                select(CustomerServiceSavedView)
                .where(
                    CustomerServiceSavedView.workspace_id == self.workspace_id,
                    or_(
                        CustomerServiceSavedView.is_shared.is_(True),
                        CustomerServiceSavedView.owner_user_id == self.actor_id,
                    ),
                )
                .order_by(CustomerServiceSavedView.name)
            )
        )

    async def delete_saved_view(self, view_id: uuid.UUID) -> None:
        result = await self.db.execute(
            delete(CustomerServiceSavedView).where(
                CustomerServiceSavedView.id == view_id,
                CustomerServiceSavedView.workspace_id == self.workspace_id,
                CustomerServiceSavedView.owner_user_id == self.actor_id,
            )
        )
        if not result.rowcount:
            raise HTTPException(status_code=404, detail="Saved view not found")
        await self.db.commit()

    async def store_attachment(
        self,
        *,
        conversation_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
        message_id: uuid.UUID | None = None,
        attachment_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> CustomerServiceAttachment:
        await self._conversation(conversation_id)

        if message_id is not None:
            owned_message_id = await self.db.scalar(
                select(ConversationMessage.id).where(
                    ConversationMessage.id == message_id,
                    ConversationMessage.conversation_id == conversation_id,
                )
            )

            if owned_message_id is None:
                raise HTTPException(
                    status_code=404,
                    detail="Message not found",
                )

        if not content or len(content) > settings.MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=413, detail="Attachment size is not allowed"
            )
        clean_name = Path(filename).name[:255] or "attachment"
        scan_status, scan_detail = self._scan_attachment(clean_name, content)
        if scan_status != "clean":
            raise HTTPException(status_code=422, detail=scan_detail)
        attachment_id = attachment_id or uuid.uuid4()
        relative = f"{self.workspace_id}/{attachment_id.hex}.bin"
        await AttachmentStorage().put(
            key=relative,
            content=content,
            content_type=content_type or "application/octet-stream",
        )
        row = CustomerServiceAttachment(
            id=attachment_id,
            workspace_id=self.workspace_id,
            conversation_id=conversation_id,
            message_id=message_id,
            uploaded_by_user_id=self.actor_id,
            filename=clean_name,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_key=relative,
            scan_status=scan_status,
            scan_detail=scan_detail,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.ATTACHMENT_RETENTION_DAYS),
        )
        self.db.add(row)

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        await self.db.refresh(row)
        return row

    def _scan_attachment(self, filename: str, content: bytes) -> tuple[str, str]:
        blocked = {".exe", ".dll", ".bat", ".cmd", ".com", ".scr", ".js"}
        if Path(filename).suffix.lower() in blocked:
            return "rejected", "Executable attachments are not allowed"
        if content.startswith((b"MZ", b"\x7fELF")):
            return "rejected", "Executable content is not allowed"
        if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content:
            return "infected", "Malware signature detected"
        if settings.ATTACHMENT_SCAN_MODE == "clamdscan":
            try:
                result = subprocess.run(
                    ["clamdscan", "--no-summary", "-"],
                    input=content,
                    capture_output=True,
                    timeout=15,
                    check=False,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return "rejected", "Malware scanner unavailable"
            if result.returncode == 1:
                return "infected", "Malware scanner rejected the attachment"
            if result.returncode != 0:
                return "rejected", "Malware scan failed closed"
            return "clean", "clamdscan passed"
        if settings.ATTACHMENT_SCAN_MODE != "builtin":
            return "rejected", "Unsupported attachment scan mode"
        return "clean", "builtin signature scan passed"

    async def get_attachment(self, attachment_id: uuid.UUID):
        row = await self.db.scalar(
            select(CustomerServiceAttachment).where(
                CustomerServiceAttachment.id == attachment_id,
                CustomerServiceAttachment.workspace_id == self.workspace_id,
                CustomerServiceAttachment.scan_status == "clean",
                CustomerServiceAttachment.deleted_at.is_(None),
                or_(
                    CustomerServiceAttachment.expires_at.is_(None),
                    CustomerServiceAttachment.expires_at > datetime.now(timezone.utc),
                ),
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Attachment not found")
        storage = AttachmentStorage()
        signed_url = await storage.signed_download_url(
            key=row.storage_key, filename=row.filename
        )
        if signed_url:
            return row, signed_url, True
        path = storage.local_path(row.storage_key)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Attachment content not found")
        return row, path, False

    async def purge_expired_attachments(self, *, limit: int = 500) -> int:
        now = datetime.now(timezone.utc)
        rows = list(
            await self.db.scalars(
                select(CustomerServiceAttachment)
                .where(
                    CustomerServiceAttachment.workspace_id == self.workspace_id,
                    CustomerServiceAttachment.expires_at <= now,
                    CustomerServiceAttachment.deleted_at.is_(None),
                )
                .limit(limit)
            )
        )
        storage = AttachmentStorage()
        for row in rows:
            await storage.delete(key=row.storage_key)
            row.deleted_at = now
        await self.db.commit()
        return len(rows)

    async def follow_conversation(
        self,
        conversation_id: uuid.UUID,
        follower_user_id: uuid.UUID,
    ) -> ConversationFollower:
        await self._conversation(conversation_id)

        membership = await self.db.scalar(
            select(WorkspaceMembership.id).where(
                WorkspaceMembership.workspace_id == self.workspace_id,
                WorkspaceMembership.user_id == follower_user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=404,
                detail="Workspace member not found",
            )

        existing = await self.db.scalar(
            select(ConversationFollower).where(
                ConversationFollower.workspace_id == self.workspace_id,
                ConversationFollower.conversation_id == conversation_id,
                ConversationFollower.user_id == follower_user_id,
            )
        )
        if existing is not None:
            return existing

        row = ConversationFollower(
            workspace_id=self.workspace_id,
            conversation_id=conversation_id,
            user_id=follower_user_id,
            followed_by_user_id=self.actor_id,
        )
        self.db.add(row)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()

            existing = await self.db.scalar(
                select(ConversationFollower).where(
                    ConversationFollower.workspace_id == self.workspace_id,
                    ConversationFollower.conversation_id == conversation_id,
                    ConversationFollower.user_id == follower_user_id,
                )
            )
            if existing is None:
                raise

            return existing

        await self.db.refresh(row)

        self._audit(
            "conversation",
            conversation_id,
            "conversation.follower_added",
            {
                "follower_user_id": str(follower_user_id),
            },
        )
        await self.db.commit()

        return row

    async def list_conversation_followers(
        self,
        conversation_id: uuid.UUID,
    ) -> list[ConversationFollower]:
        await self._conversation(conversation_id)

        return list(
            await self.db.scalars(
                select(ConversationFollower)
                .where(
                    ConversationFollower.workspace_id == self.workspace_id,
                    ConversationFollower.conversation_id == conversation_id,
                )
                .order_by(
                    ConversationFollower.created_at,
                    ConversationFollower.id,
                )
            )
        )

    async def unfollow_conversation(
        self,
        conversation_id: uuid.UUID,
        follower_user_id: uuid.UUID,
    ) -> bool:
        await self._conversation(conversation_id)

        result = await self.db.execute(
            delete(ConversationFollower).where(
                ConversationFollower.workspace_id == self.workspace_id,
                ConversationFollower.conversation_id == conversation_id,
                ConversationFollower.user_id == follower_user_id,
            )
        )

        removed = bool(result.rowcount)

        if removed:
            self._audit(
                "conversation",
                conversation_id,
                "conversation.follower_removed",
                {
                    "follower_user_id": str(follower_user_id),
                },
            )

        await self.db.commit()

        return removed

    async def acquire_lease(self, conversation_id: uuid.UUID, ttl_seconds: int) -> dict:
        await self._conversation(conversation_id)
        if self.actor_id is None:
            raise HTTPException(status_code=403, detail="A user identity is required")
        now = datetime.now(timezone.utc)
        row = await self.db.scalar(
            select(ConversationEditLease)
            .where(ConversationEditLease.conversation_id == conversation_id)
            .with_for_update()
        )
        if row and row.expires_at > now and row.actor_user_id != self.actor_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "conversation_in_use",
                    "actor_user_id": str(row.actor_user_id),
                    "expires_at": row.expires_at.isoformat(),
                },
            )
        token = secrets.token_urlsafe(32)
        if row is None:
            row = ConversationEditLease(
                conversation_id=conversation_id,
                workspace_id=self.workspace_id,
                actor_user_id=self.actor_id,
                lease_token=token,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            self.db.add(row)
        else:
            row.actor_user_id = self.actor_id
            row.lease_token = token
            row.expires_at = now + timedelta(seconds=ttl_seconds)
        await self.db.commit()
        return {"lease_token": token, "expires_at": row.expires_at}

    async def release_lease(self, conversation_id: uuid.UUID, lease_token: str) -> None:
        result = await self.db.execute(
            delete(ConversationEditLease).where(
                ConversationEditLease.conversation_id == conversation_id,
                ConversationEditLease.workspace_id == self.workspace_id,
                ConversationEditLease.lease_token == lease_token,
            )
        )
        if not result.rowcount:
            raise HTTPException(status_code=404, detail="Lease not found")
        await self.db.commit()

    async def create_notification(self, payload: NotificationCreate):
        membership = await self.db.scalar(
            select(WorkspaceMembership.id).where(
                WorkspaceMembership.workspace_id == self.workspace_id,
                WorkspaceMembership.user_id == payload.recipient_user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is None:
            raise HTTPException(status_code=404, detail="Workspace member not found")
        row = CustomerServiceNotification(
            workspace_id=self.workspace_id,
            **payload.model_dump(),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list_notifications(self, unread_only: bool, limit: int):
        statement = select(CustomerServiceNotification).where(
            CustomerServiceNotification.workspace_id == self.workspace_id,
            CustomerServiceNotification.recipient_user_id == self.actor_id,
        )
        if unread_only:
            statement = statement.where(CustomerServiceNotification.read_at.is_(None))
        return list(
            await self.db.scalars(
                statement.order_by(CustomerServiceNotification.created_at.desc()).limit(
                    limit
                )
            )
        )

    async def read_notification(self, notification_id: uuid.UUID):
        row = await self.db.scalar(
            select(CustomerServiceNotification).where(
                CustomerServiceNotification.id == notification_id,
                CustomerServiceNotification.workspace_id == self.workspace_id,
                CustomerServiceNotification.recipient_user_id == self.actor_id,
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        row.read_at = datetime.now(timezone.utc)
        await self.db.commit()
        return row

    async def create_sla_calendar(self, payload: SLACalendarCreate):
        try:
            ZoneInfo(payload.timezone)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(status_code=422, detail="Unknown timezone") from exc
        if payload.is_default:
            await self.db.execute(
                update(CustomerServiceSLACalendar)
                .where(CustomerServiceSLACalendar.workspace_id == self.workspace_id)
                .values(is_default=False)
            )
        row = CustomerServiceSLACalendar(
            workspace_id=self.workspace_id,
            **payload.model_dump(),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list_sla_calendars(self):
        return list(
            await self.db.scalars(
                select(CustomerServiceSLACalendar)
                .where(CustomerServiceSLACalendar.workspace_id == self.workspace_id)
                .order_by(CustomerServiceSLACalendar.name)
            )
        )

    async def calculate_sla_due_at(
        self, calendar_id: uuid.UUID, start: datetime, minutes: int
    ) -> datetime:
        calendar = await self.db.scalar(
            select(CustomerServiceSLACalendar).where(
                CustomerServiceSLACalendar.id == calendar_id,
                CustomerServiceSLACalendar.workspace_id == self.workspace_id,
            )
        )
        if calendar is None:
            raise HTTPException(status_code=404, detail="SLA calendar not found")
        zone = ZoneInfo(calendar.timezone)
        current = start.astimezone(zone)
        remaining = minutes
        holidays = {date.fromisoformat(item) for item in calendar.holidays}
        for _ in range(370):
            day_key = current.strftime("%a").lower()[:3]
            windows = (calendar.weekly_hours or {}).get(day_key, [])
            if current.date() not in holidays:
                for start_text, end_text in windows:
                    start_time = time.fromisoformat(start_text)
                    end_time = time.fromisoformat(end_text)
                    window_start = datetime.combine(current.date(), start_time, zone)
                    window_end = datetime.combine(current.date(), end_time, zone)
                    cursor = max(current, window_start)
                    if cursor >= window_end:
                        continue
                    available = int((window_end - cursor).total_seconds() // 60)
                    if remaining <= available:
                        return (cursor + timedelta(minutes=remaining)).astimezone(
                            timezone.utc
                        )
                    remaining -= available
            current = datetime.combine(
                current.date() + timedelta(days=1), time.min, zone
            )
        raise HTTPException(status_code=422, detail="SLA calendar has no usable hours")

    async def merge_customers(self, source_id: uuid.UUID, target_id: uuid.UUID):
        if source_id == target_id:
            raise HTTPException(status_code=422, detail="Source and target must differ")
        rows = list(
            await self.db.scalars(
                select(Customer)
                .where(
                    Customer.user_id == self.workspace_id,
                    Customer.id.in_([source_id, target_id]),
                    Customer.merged_into_id.is_(None),
                )
                .with_for_update()
            )
        )
        by_id = {row.id: row for row in rows}
        if source_id not in by_id or target_id not in by_id:
            raise HTTPException(status_code=404, detail="Customer not found")
        source, target = by_id[source_id], by_id[target_id]
        await self.db.execute(
            update(Conversation)
            .where(
                Conversation.user_id == self.workspace_id,
                Conversation.customer_id == source.id,
            )
            .values(customer_id=target.id)
        )
        await self.db.execute(
            update(CustomerServiceExternalConversationLink)
            .where(
                CustomerServiceExternalConversationLink.user_id == self.workspace_id,
                CustomerServiceExternalConversationLink.customer_id == source.id,
            )
            .values(customer_id=target.id)
        )
        await self.db.execute(
            update(CustomerIdentity)
            .where(
                CustomerIdentity.user_id == self.workspace_id,
                CustomerIdentity.customer_id == source.id,
            )
            .values(customer_id=target.id)
        )

        target.name = target.name or source.name
        target.email = target.email or source.email
        target.phone = target.phone or source.phone

        # Set only after durable relations have been moved.
        # The source/target customer rows are held FOR UPDATE
        # for the entire merge transaction.
        source.merged_into_id = target.id
        self._merge_event("customer", source.id, target.id, "merge")
        self._audit(
            "customer", target.id, "customers_merged", {"source_id": str(source.id)}
        )
        await self.db.commit()
        return {
            "source_id": str(source.id),
            "target_id": str(target.id),
            "status": "merged",
        }

    async def merge_conversations(self, source_id: uuid.UUID, target_id: uuid.UUID):
        if source_id == target_id:
            raise HTTPException(status_code=422, detail="Source and target must differ")
        rows = list(
            await self.db.scalars(
                select(Conversation)
                .where(
                    Conversation.user_id == self.workspace_id,
                    Conversation.id.in_([source_id, target_id]),
                    Conversation.merged_into_id.is_(None),
                )
                .with_for_update()
            )
        )
        by_id = {row.id: row for row in rows}
        if source_id not in by_id or target_id not in by_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # The unique source identity protects provider idempotency. The actual
        # collision check below uses a self-correlated EXISTS without deleting history.
        target_message = ConversationMessage.__table__.alias("target_message_identity")
        collision = await self.db.scalar(
            select(ConversationMessage.id)
            .where(
                ConversationMessage.conversation_id == source_id,
                ConversationMessage.source_message_id.is_not(None),
                select(target_message.c.id)
                .where(
                    target_message.c.conversation_id == target_id,
                    target_message.c.source_type == ConversationMessage.source_type,
                    target_message.c.source_message_id
                    == ConversationMessage.source_message_id,
                )
                .exists(),
            )
            .limit(1)
        )
        if collision is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "conversation_merge_source_identity_collision",
                    "message": "Resolve duplicate provider messages before merging.",
                },
            )
        await self.db.execute(
            update(ConversationMessage)
            .where(ConversationMessage.conversation_id == source_id)
            .values(conversation_id=target_id)
        )
        await self.db.execute(
            update(CustomerServiceExternalConversationLink)
            .where(
                CustomerServiceExternalConversationLink.user_id == self.workspace_id,
                CustomerServiceExternalConversationLink.conversation_id == source_id,
            )
            .values(conversation_id=target_id)
        )
        await self.db.execute(
            update(CustomerServiceExternalMessageLink)
            .where(
                CustomerServiceExternalMessageLink.user_id == self.workspace_id,
                CustomerServiceExternalMessageLink.conversation_id == source_id,
            )
            .values(conversation_id=target_id)
        )
        await self.db.execute(
            update(CustomerServiceAttachment)
            .where(
                CustomerServiceAttachment.workspace_id == self.workspace_id,
                CustomerServiceAttachment.conversation_id == source_id,
            )
            .values(conversation_id=target_id)
        )
        source = by_id[source_id]
        source.merged_into_id = target_id
        source.status = "resolved"
        source_ticket = await self.db.scalar(
            select(Ticket).where(Ticket.conversation_id == source_id)
        )
        if source_ticket:
            source_ticket.status = "closed"
            source_ticket.resolution_reason = "merged"
            source_ticket.resolved_at = datetime.now(timezone.utc)
        self._merge_event("conversation", source_id, target_id, "merge")
        self._audit(
            "conversation",
            target_id,
            "conversations_merged",
            {"source_id": str(source_id)},
        )
        await self.db.commit()
        return {
            "source_id": str(source_id),
            "target_id": str(target_id),
            "status": "merged",
        }

    async def split_conversation(
        self, conversation_id: uuid.UUID, payload: ConversationSplitRequest
    ):
        source = await self._conversation(conversation_id)
        message_ids = list(
            await self.db.scalars(
                select(ConversationMessage.id).where(
                    ConversationMessage.conversation_id == conversation_id,
                    ConversationMessage.id.in_(payload.message_ids),
                )
            )
        )
        if len(message_ids) != len(set(payload.message_ids)):
            raise HTTPException(
                status_code=404, detail="One or more messages were not found"
            )
        target = Conversation(
            user_id=self.workspace_id,
            workspace_id=self.workspace_id,
            customer_id=source.customer_id,
            channel=source.channel,
            subject=payload.subject or source.subject,
            status="open",
        )
        self.db.add(target)
        await self.db.flush()
        await self.db.execute(
            update(ConversationMessage)
            .where(ConversationMessage.id.in_(message_ids))
            .values(conversation_id=target.id)
        )

        # Message-bound attachments follow the exact messages
        # moved into the newly split conversation. Conversation-
        # level attachments (message_id=NULL) remain on source.
        await self.db.execute(
            update(CustomerServiceAttachment)
            .where(
                CustomerServiceAttachment.workspace_id == self.workspace_id,
                CustomerServiceAttachment.conversation_id == conversation_id,
                CustomerServiceAttachment.message_id.in_(message_ids),
            )
            .values(conversation_id=target.id)
        )

        self.db.add(
            Ticket(
                user_id=self.workspace_id,
                workspace_id=self.workspace_id,
                conversation_id=target.id,
                title=target.subject or "Split conversation",
                status="open",
                priority="normal",
            )
        )
        self._merge_event(
            "conversation",
            source.id,
            target.id,
            "split",
            {"message_ids": [str(i) for i in message_ids]},
        )
        self._audit(
            "conversation",
            target.id,
            "conversation_split",
            {"source_id": str(source.id)},
        )
        await self.db.commit()
        return {
            "source_id": str(source.id),
            "conversation_id": str(target.id),
            "status": "split",
        }

    async def resolve_ticket(self, ticket_id: uuid.UUID, payload: ResolutionRequest):
        ticket = await self.db.scalar(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.user_id == self.workspace_id,
            )
        )
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        now = datetime.now(timezone.utc)
        ticket.status = "closed"
        ticket.resolution_reason = payload.reason
        ticket.resolution_outcome = payload.outcome
        ticket.resolved_at = now
        survey_token = None
        if payload.send_csat:
            raw = secrets.token_urlsafe(48)
            survey = CustomerServiceCSATSurvey(
                workspace_id=self.workspace_id,
                conversation_id=ticket.conversation_id,
                ticket_id=ticket.id,
                token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                status="sent",
                sent_at=now,
            )
            self.db.add(survey)
            survey_token = raw
        await self.db.commit()
        return {
            "ticket_id": str(ticket.id),
            "status": "closed",
            "csat_token": survey_token,
        }

    async def answer_csat(self, token: str, score: int, comment: str | None):
        row = await self.db.scalar(
            select(CustomerServiceCSATSurvey)
            .where(
                CustomerServiceCSATSurvey.token_hash
                == hashlib.sha256(token.encode()).hexdigest()
            )
            .with_for_update()
        )
        if row is None or row.status == "answered":
            raise HTTPException(status_code=400, detail="Invalid or used CSAT token")
        row.score = score
        row.comment = comment
        row.status = "answered"
        row.answered_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {"status": "answered"}

    async def csat_report(self):
        count, average = (
            await self.db.execute(
                select(
                    func.count(CustomerServiceCSATSurvey.id),
                    func.avg(CustomerServiceCSATSurvey.score),
                ).where(
                    CustomerServiceCSATSurvey.workspace_id == self.workspace_id,
                    CustomerServiceCSATSurvey.status == "answered",
                )
            )
        ).one()
        return {
            "responses": count,
            "average_score": float(average) if average else None,
        }

    async def onboarding(self):
        state = await self.db.get(CustomerServiceOnboardingState, self.workspace_id)
        if state is None:
            state = CustomerServiceOnboardingState(workspace_id=self.workspace_id)
            self.db.add(state)
            await self.db.commit()
            await self.db.refresh(state)
        shopify = await self.db.scalar(
            select(CustomerServiceShopifyConnection.id).where(
                CustomerServiceShopifyConnection.user_id == self.workspace_id,
                CustomerServiceShopifyConnection.status == "active",
            )
        )
        channels = await self.db.scalar(
            select(func.count(CustomerServiceChannelConnection.id)).where(
                CustomerServiceChannelConnection.user_id == self.workspace_id,
                CustomerServiceChannelConnection.status == "active",
            )
        )
        checklist = {
            "shopify_connected": bool(shopify),
            "support_channel_connected": bool(channels),
            **(state.checklist or {}),
        }
        return {
            "status": state.status,
            "checklist": checklist,
            "demo_data_seeded": state.demo_data_seeded,
            "provider_health": await self.provider_health(),
        }

    async def update_onboarding(self, checklist: dict[str, bool]):
        state = await self.db.get(CustomerServiceOnboardingState, self.workspace_id)
        if state is None:
            state = CustomerServiceOnboardingState(workspace_id=self.workspace_id)
            self.db.add(state)
        state.checklist = {**(state.checklist or {}), **checklist}
        complete = bool(state.checklist) and all(state.checklist.values())
        state.status = "completed" if complete else "in_progress"
        state.completed_at = datetime.now(timezone.utc) if complete else None
        await self.db.commit()
        return await self.onboarding()

    async def seed_demo_data(self):
        state = await self.db.get(CustomerServiceOnboardingState, self.workspace_id)
        if state and state.demo_data_seeded:
            return {"status": "already_seeded", "onboarding": await self.onboarding()}
        customer = await self.db.scalar(
            select(Customer).where(
                Customer.user_id == self.workspace_id,
                Customer.email == "demo-customer@tajeran.invalid",
            )
        )
        if customer is None:
            customer = Customer(
                user_id=self.workspace_id,
                workspace_id=self.workspace_id,
                name="Demo Customer",
                email="demo-customer@tajeran.invalid",
            )
            self.db.add(customer)
            await self.db.flush()
        conversation = await self.db.scalar(
            select(Conversation).where(
                Conversation.user_id == self.workspace_id,
                Conversation.customer_id == customer.id,
                Conversation.subject == "Demo: Where is my order?",
            )
        )
        if conversation is None:
            conversation = Conversation(
                user_id=self.workspace_id,
                workspace_id=self.workspace_id,
                customer_id=customer.id,
                channel="website",
                subject="Demo: Where is my order?",
                status="open",
            )
            self.db.add(conversation)
            await self.db.flush()
            self.db.add_all(
                [
                    ConversationMessage(
                        conversation_id=conversation.id,
                        sender_type="customer",
                        body="Hi, can you help me find my order?",
                        meta={"demo": True},
                    ),
                    Ticket(
                        user_id=self.workspace_id,
                        workspace_id=self.workspace_id,
                        conversation_id=conversation.id,
                        title=conversation.subject,
                        status="open",
                        priority="normal",
                    ),
                ]
            )
        if state is None:
            state = CustomerServiceOnboardingState(workspace_id=self.workspace_id)
            self.db.add(state)
        state.demo_data_seeded = True
        state.status = "in_progress"
        state.checklist = {**(state.checklist or {}), "demo_explored": True}
        self._audit("onboarding", None, "demo_data_seeded", {})
        await self.db.commit()
        return {
            "status": "seeded",
            "customer_id": str(customer.id),
            "conversation_id": str(conversation.id),
            "onboarding": await self.onboarding(),
        }

    async def update_customer_consent(self, customer_id: uuid.UUID, consent: dict):
        customer = await self.db.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.user_id == self.workspace_id,
                Customer.merged_into_id.is_(None),
            )
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer.consent = {
            **consent,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "recorded_by": str(self.actor_id) if self.actor_id else None,
        }
        self._audit(
            "customer", customer.id, "consent_updated", {"consent": customer.consent}
        )
        await self.db.commit()
        return {"customer_id": str(customer.id), "consent": customer.consent}

    async def provider_health(self):
        shopify = await self.db.scalar(
            select(CustomerServiceShopifyConnection).where(
                CustomerServiceShopifyConnection.user_id == self.workspace_id
            )
        )
        channels = list(
            await self.db.scalars(
                select(CustomerServiceChannelConnection).where(
                    CustomerServiceChannelConnection.user_id == self.workspace_id
                )
            )
        )
        return {
            "shopify": {
                "configured": shopify is not None,
                "active": bool(shopify and shopify.status == "active"),
                "reauth_required": bool(shopify and shopify.reauth_required_at),
            },
            "channels": [
                {
                    "provider": row.channel,
                    "channel": row.channel,
                    "active": row.status == "active",
                }
                for row in channels
            ],
        }

    async def subscription(self):
        row = await self.db.get(WorkspaceSubscription, self.workspace_id)
        if row is None:
            row = WorkspaceSubscription(
                workspace_id=self.workspace_id,
                plan="trial",
                status="trialing",
                trial_ends_at=datetime.now(timezone.utc)
                + timedelta(days=settings.DEFAULT_TRIAL_DAYS),
                entitlements=DEFAULT_ENTITLEMENTS,
            )
            self.db.add(row)
            await self.db.commit()
            await self.db.refresh(row)
        return row

    async def update_subscription(self, payload: SubscriptionUpdate):
        row = await self.subscription()
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def require_entitlement(self, entitlement: str) -> None:
        row = await self.subscription()
        now = datetime.now(timezone.utc)
        valid = row.status == "active" or (
            row.status == "trialing" and row.trial_ends_at and row.trial_ends_at > now
        )
        if not valid or not (row.entitlements or {}).get(entitlement, False):
            raise HTTPException(
                status_code=402,
                detail={"code": "subscription_required", "entitlement": entitlement},
            )

    async def require_monthly_conversation_quota(self) -> None:
        row = await self.subscription()
        now = datetime.now(timezone.utc)
        valid = row.status == "active" or (
            row.status == "trialing" and row.trial_ends_at and row.trial_ends_at > now
        )
        limit = int((row.entitlements or {}).get("monthly_conversations", 0))
        if not valid or limit <= 0:
            raise HTTPException(
                status_code=402, detail={"code": "subscription_required"}
            )
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        used = await self.db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.user_id == self.workspace_id,
                Conversation.created_at >= month_start,
            )
        )
        if int(used or 0) >= limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "monthly_conversation_quota_exceeded",
                    "limit": limit,
                    "used": int(used or 0),
                },
            )

    async def privacy_request(self, customer_id: uuid.UUID, kind: str):
        customer = await self.db.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.user_id == self.workspace_id,
            )
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        request = CustomerServicePrivacyRequest(
            workspace_id=self.workspace_id,
            customer_id=customer.id,
            requested_by_user_id=self.actor_id,
            kind=kind,
            status="pending",
        )
        self.db.add(request)
        self._audit(
            "privacy_request",
            request.id,
            "privacy_request_created",
            {"kind": kind, "customer_id": str(customer.id)},
        )
        await self.db.flush()
        await JobService(self.db).enqueue(
            job_type="customer_service.privacy.process",
            user_id=self.workspace_id,
            payload={"request_id": str(request.id)},
            idempotency_key=f"cs-privacy:{request.id}",
            commit=False,
        )
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def process_privacy_request(self, request_id: uuid.UUID):
        request = await self.db.scalar(
            select(CustomerServicePrivacyRequest)
            .where(
                CustomerServicePrivacyRequest.id == request_id,
                CustomerServicePrivacyRequest.workspace_id == self.workspace_id,
                CustomerServicePrivacyRequest.status == "pending",
            )
            .with_for_update()
        )
        if request is None:
            raise HTTPException(
                status_code=404, detail="Pending privacy request not found"
            )
        customer = await self.db.scalar(
            select(Customer).where(
                Customer.id == request.customer_id,
                Customer.user_id == self.workspace_id,
            )
        )
        if customer is None:
            request.status = "failed"
            request.error = "Customer no longer exists"
            await self.db.commit()
            return request
        request.status = "processing"
        kind = request.kind
        if kind == "export":
            conversations = list(
                await self.db.scalars(
                    select(Conversation).where(
                        Conversation.user_id == self.workspace_id,
                        Conversation.customer_id == customer.id,
                    )
                )
            )
            conversation_ids = [row.id for row in conversations]
            messages = (
                list(
                    await self.db.scalars(
                        select(ConversationMessage)
                        .where(
                            ConversationMessage.conversation_id.in_(conversation_ids)
                        )
                        .order_by(ConversationMessage.created_at)
                    )
                )
                if conversation_ids
                else []
            )
            request.result = {
                "customer": {
                    "id": str(customer.id),
                    "name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone,
                    "consent": customer.consent,
                },
                "conversation_ids": [str(row.id) for row in conversations],
                "messages": [
                    {
                        "id": str(row.id),
                        "conversation_id": str(row.conversation_id),
                        "sender_type": str(row.sender_type),
                        "body": row.body,
                        "created_at": row.created_at.isoformat()
                        if row.created_at
                        else None,
                    }
                    for row in messages
                ],
            }
        else:
            marker = f"anon-{customer.id.hex[:12]}"
            customer.name = "Deleted customer"
            customer.email = f"{marker}@invalid.local"
            customer.phone = None
            customer.consent = None
            customer.anonymized_at = datetime.now(timezone.utc)
            await self.db.execute(
                update(ConversationMessage)
                .where(
                    ConversationMessage.conversation_id.in_(
                        select(Conversation.id).where(
                            Conversation.user_id == self.workspace_id,
                            Conversation.customer_id == customer.id,
                        )
                    )
                )
                .values(body="[deleted by privacy request]", meta=None)
            )
            request.result = {"customer_id": str(customer.id), "anonymized": True}
        request.status = "completed"
        request.completed_at = datetime.now(timezone.utc)
        self._audit(
            "privacy_request",
            request.id,
            "privacy_request_completed",
            {"kind": kind, "customer_id": str(customer.id)},
        )
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def list_privacy_requests(self):
        return list(
            await self.db.scalars(
                select(CustomerServicePrivacyRequest)
                .where(CustomerServicePrivacyRequest.workspace_id == self.workspace_id)
                .order_by(CustomerServicePrivacyRequest.created_at.desc())
            )
        )

    async def retention_preview(self, *, limit: int = 100):
        """Report stale records; deletion still requires an explicit per-customer request."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=settings.CUSTOMER_DATA_RETENTION_DAYS
        )
        customers = list(
            await self.db.scalars(
                select(Customer)
                .where(
                    Customer.user_id == self.workspace_id,
                    Customer.anonymized_at.is_(None),
                    Customer.merged_into_id.is_(None),
                    Customer.updated_at < cutoff,
                    ~select(CustomerServicePrivacyRequest.id)
                    .where(
                        CustomerServicePrivacyRequest.workspace_id == self.workspace_id,
                        CustomerServicePrivacyRequest.customer_id == Customer.id,
                        CustomerServicePrivacyRequest.kind.in_(["delete", "anonymize"]),
                        CustomerServicePrivacyRequest.status.in_(
                            ["pending", "processing"]
                        ),
                    )
                    .exists(),
                )
                .limit(limit)
            )
        )
        eligible = []
        for customer in customers:
            latest_conversation = await self.db.scalar(
                select(func.max(Conversation.updated_at)).where(
                    Conversation.user_id == self.workspace_id,
                    Conversation.customer_id == customer.id,
                )
            )
            if latest_conversation and latest_conversation >= cutoff:
                continue
            eligible.append(
                {
                    "customer_id": str(customer.id),
                    "last_activity_at": (
                        latest_conversation or customer.updated_at
                    ).isoformat(),
                }
            )
        return {
            "retention_days": settings.CUSTOMER_DATA_RETENTION_DAYS,
            "cutoff": cutoff.isoformat(),
            "eligible": eligible,
            "action": "Create an explicit anonymize privacy request per customer.",
        }

    async def _conversation(self, conversation_id: uuid.UUID):
        row = await self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == self.workspace_id,
                Conversation.merged_into_id.is_(None),
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return row

    def _merge_event(
        self,
        entity_type: str,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        operation: str,
        payload: dict | None = None,
    ) -> None:
        self.db.add(
            CustomerServiceMergeEvent(
                workspace_id=self.workspace_id,
                actor_user_id=self.actor_id,
                entity_type=entity_type,
                source_id=source_id,
                target_id=target_id,
                operation=operation,
                payload=payload or {},
            )
        )

    def _audit(
        self,
        entity_type: str,
        entity_id: uuid.UUID | None,
        action: str,
        meta: dict,
    ) -> None:
        self.db.add(
            CustomerServiceAuditLog(
                user_id=self.workspace_id,
                actor_id=self.actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                meta=meta,
            )
        )
