from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    ConversationTag,
    Customer,
    CustomerServiceAuditLog,
    CustomerServiceReplyDraft,
    CustomerServiceReplySignature,
    Ticket,
    TicketAssignment,
)
from app.domains.customer_service.schemas.commercial import ReplySendRequest
from app.domains.customer_service.schemas.helpdesk import (
    BulkConversationActionRequest,
    ConversationModerationRequest,
    ConversationSnoozeRequest,
    ReplyDraftWrite,
    ReplySignatureWrite,
)
from app.domains.customer_service.services.messaging import (
    CustomerServiceMessagingService,
)
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB,
)
from app.platform.jobs.service import JobService
from app.tenancy.models import WorkspaceMembership


SNOOZE_WAKE_JOB = "customer_service.conversation.wake"


class CustomerServiceModerationService:
    _PHISHING = (
        "verify your password",
        "confirm your password",
        "seed phrase",
        "wallet recovery",
        "gift card payment",
        "خود را تأیید کنید",
        "رمز عبور",
    )
    _SPAM = (
        "buy followers",
        "guest post",
        "seo services",
        "casino",
        "crypto investment",
        "limited time investment",
    )

    @classmethod
    def classify(cls, body: str) -> dict:
        text = re.sub(r"\s+", " ", (body or "").lower()).strip()
        links = len(re.findall(r"https?://", text))
        phishing_hits = sum(phrase in text for phrase in cls._PHISHING)
        spam_hits = sum(phrase in text for phrase in cls._SPAM)
        if phishing_hits and (links or "password" in text or "رمز" in text):
            return {
                "status": "phishing",
                "score": min(1.0, 0.75 + phishing_hits * 0.1),
                "reason": "credential_or_payment_phishing_pattern",
            }
        if spam_hits >= 1 or links >= 5:
            return {
                "status": "spam",
                "score": min(1.0, 0.65 + spam_hits * 0.1 + links * 0.03),
                "reason": "unsolicited_or_link_spam_pattern",
            }
        return {"status": "normal", "score": 0.0, "reason": None}


class CustomerServiceHelpdeskService:
    def __init__(self, db: AsyncSession, *, workspace_id: UUID, actor_user_id: UUID):
        self.db = db
        self.workspace_id = workspace_id
        self.actor_user_id = actor_user_id

    async def snooze(
        self, conversation_id: UUID, payload: ConversationSnoozeRequest
    ) -> Conversation:
        row = await self._conversation(conversation_id, lock=True)
        row.snoozed_until = payload.until
        row.snooze_reason = payload.reason
        row.snoozed_by_user_id = self.actor_user_id
        await JobService(self.db).enqueue(
            user_id=self.workspace_id,
            job_type=SNOOZE_WAKE_JOB,
            run_after=payload.until,
            idempotency_key=f"conversation-wake:{conversation_id}:{payload.until.isoformat()}",
            payload={
                "conversation_id": str(conversation_id),
                "expected_snoozed_until": payload.until.isoformat(),
            },
            commit=False,
        )
        self._audit(
            row.id, "conversation.snoozed", {"until": payload.until.isoformat()}
        )
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def wake(self, conversation_id: UUID, *, expected_until: str | None = None):
        row = await self._conversation(conversation_id, lock=True)
        if expected_until and (
            row.snoozed_until is None or row.snoozed_until.isoformat() != expected_until
        ):
            return {"conversation_id": str(row.id), "status": "superseded"}
        row.snoozed_until = None
        row.snooze_reason = None
        row.snoozed_by_user_id = None
        self._audit(row.id, "conversation.woke", {})
        await self.db.commit()
        return {"conversation_id": str(row.id), "status": "open"}

    async def moderate(
        self, conversation_id: UUID, payload: ConversationModerationRequest
    ) -> Conversation:
        row = await self._conversation(conversation_id, lock=True)
        row.moderation_status = payload.status
        row.moderation_reason = payload.reason
        row.moderation_score = 1.0 if payload.status != "normal" else 0.0
        self._audit(
            row.id,
            "conversation.moderation_changed",
            {"status": payload.status, "reason": payload.reason},
        )
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def assess_inbound(self, conversation_id: UUID, body: str) -> dict:
        assessment = CustomerServiceModerationService.classify(body)
        if assessment["status"] == "normal":
            return assessment
        row = await self._conversation(conversation_id, lock=True)
        row.moderation_status = assessment["status"]
        row.moderation_reason = assessment["reason"]
        row.moderation_score = assessment["score"]
        self._audit(row.id, "conversation.auto_quarantined", assessment)
        await self.db.commit()
        return assessment

    async def bulk(self, payload: BulkConversationActionRequest) -> dict:
        ids = list(dict.fromkeys(payload.conversation_ids))
        rows = list(
            await self.db.scalars(
                select(Conversation)
                .where(
                    Conversation.user_id == self.workspace_id,
                    Conversation.id.in_(ids),
                    Conversation.merged_into_id.is_(None),
                )
                .with_for_update()
            )
        )
        if len(rows) != len(ids):
            raise HTTPException(
                status_code=404, detail="One or more conversations not found"
            )
        if (
            payload.action in {"status", "assign", "tag", "moderation"}
            and not payload.value
        ):
            raise HTTPException(
                status_code=422, detail="value is required for this action"
            )
        if payload.action == "snooze" and payload.until is None:
            raise HTTPException(status_code=422, detail="until is required for snooze")
        if payload.action == "snooze":
            snooze_request = ConversationSnoozeRequest(until=payload.until)
        for row in rows:
            if payload.action == "status":
                if payload.value not in {"open", "pending", "resolved"}:
                    raise HTTPException(
                        status_code=422, detail="Invalid conversation status"
                    )
                row.status = payload.value
                ticket = await self.db.scalar(
                    select(Ticket).where(Ticket.conversation_id == row.id)
                )
                if ticket:
                    ticket.status = payload.value
            elif payload.action == "assign":
                ticket = await self.db.scalar(
                    select(Ticket).where(Ticket.conversation_id == row.id)
                )
                if ticket:
                    try:
                        assignee_id = UUID(str(payload.value))
                    except (TypeError, ValueError) as exc:
                        raise HTTPException(
                            status_code=422,
                            detail="Assignment value must be a user UUID",
                        ) from exc
                    membership = await self.db.scalar(
                        select(WorkspaceMembership.id).where(
                            WorkspaceMembership.workspace_id == self.workspace_id,
                            WorkspaceMembership.user_id == assignee_id,
                            WorkspaceMembership.status == "active",
                        )
                    )
                    if membership is None:
                        raise HTTPException(
                            status_code=422,
                            detail="Assignee is not an active workspace member",
                        )
                    previous = list(
                        await self.db.scalars(
                            select(TicketAssignment).where(
                                TicketAssignment.user_id == self.workspace_id,
                                TicketAssignment.ticket_id == ticket.id,
                                TicketAssignment.is_active.is_(True),
                            )
                        )
                    )
                    for assignment in previous:
                        assignment.is_active = False
                    ticket.assigned_to = payload.value
                    self.db.add(
                        TicketAssignment(
                            user_id=self.workspace_id,
                            ticket_id=ticket.id,
                            assigned_to=assignee_id,
                            assigned_by=self.actor_user_id,
                            is_active=True,
                            meta={"source": "bulk_action"},
                        )
                    )
            elif payload.action == "tag":
                existing_tag = await self.db.scalar(
                    select(ConversationTag.id).where(
                        ConversationTag.user_id == self.workspace_id,
                        ConversationTag.conversation_id == row.id,
                        ConversationTag.name == payload.value,
                    )
                )
                if existing_tag is None:
                    self.db.add(
                        ConversationTag(
                            user_id=self.workspace_id,
                            conversation_id=row.id,
                            name=payload.value,
                        )
                    )
            elif payload.action == "moderation":
                if payload.value not in {"normal", "spam", "phishing", "quarantined"}:
                    raise HTTPException(
                        status_code=422, detail="Invalid moderation value"
                    )
                row.moderation_status = payload.value
                row.moderation_score = 0.0 if payload.value == "normal" else 1.0
            elif payload.action == "snooze":
                row.snoozed_until = snooze_request.until
                row.snoozed_by_user_id = self.actor_user_id
                await JobService(self.db).enqueue(
                    user_id=self.workspace_id,
                    job_type=SNOOZE_WAKE_JOB,
                    run_after=snooze_request.until,
                    idempotency_key=(
                        f"conversation-wake:{row.id}:{snooze_request.until.isoformat()}"
                    ),
                    payload={
                        "conversation_id": str(row.id),
                        "expected_snoozed_until": snooze_request.until.isoformat(),
                    },
                    commit=False,
                )
            self._audit(
                row.id, f"conversation.bulk_{payload.action}", {"value": payload.value}
            )
        await self.db.commit()
        return {"processed": len(rows), "action": payload.action}

    async def create_draft(self, conversation_id: UUID, payload: ReplyDraftWrite):
        await self._conversation(conversation_id)
        row = CustomerServiceReplyDraft(
            workspace_id=self.workspace_id,
            conversation_id=conversation_id,
            author_user_id=self.actor_user_id,
            body=payload.body,
            source=payload.source,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update_draft(self, draft_id: UUID, payload: ReplyDraftWrite):
        row = await self._draft(draft_id, lock=True)
        if row.status != "draft":
            raise HTTPException(
                status_code=409, detail="Only active drafts can be edited"
            )
        if (
            payload.expected_version is not None
            and payload.expected_version != row.version
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "draft_version_conflict",
                    "current_version": row.version,
                },
            )
        row.body = payload.body
        row.source = payload.source
        row.version += 1
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list_drafts(self, conversation_id: UUID):
        await self._conversation(conversation_id)
        return list(
            await self.db.scalars(
                select(CustomerServiceReplyDraft)
                .where(
                    CustomerServiceReplyDraft.workspace_id == self.workspace_id,
                    CustomerServiceReplyDraft.conversation_id == conversation_id,
                    CustomerServiceReplyDraft.status == "draft",
                )
                .order_by(CustomerServiceReplyDraft.updated_at.desc())
            )
        )

    async def discard_draft(self, draft_id: UUID):
        row = await self._draft(draft_id, lock=True)
        row.status = "discarded"
        await self.db.commit()

    async def schedule_draft(
        self,
        draft_id: UUID,
        *,
        scheduled_for: datetime,
        expected_version: int,
    ):
        now = datetime.now(timezone.utc)

        if scheduled_for.tzinfo is None:
            raise HTTPException(
                status_code=422,
                detail="scheduled_for must include timezone",
            )

        scheduled_for = scheduled_for.astimezone(timezone.utc)

        if scheduled_for <= now:
            raise HTTPException(
                status_code=422,
                detail="scheduled_for must be in the future",
            )

        row = await self._draft(
            draft_id,
            lock=True,
        )

        if row.status not in {"draft", "scheduled"}:
            raise HTTPException(
                status_code=409,
                detail="Draft is not schedulable",
            )

        if row.version != expected_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "draft_version_conflict",
                    "current_version": row.version,
                },
            )

        row.status = "scheduled"
        row.scheduled_for = scheduled_for
        row.scheduled_by_user_id = self.actor_user_id
        row.version += 1

        await self.db.flush()

        await JobService(self.db).enqueue(
            user_id=self.workspace_id,
            job_type=(CUSTOMER_SERVICE_SCHEDULED_REPLY_JOB),
            run_after=scheduled_for,
            idempotency_key=(f"scheduled-reply:{row.id}:{row.version}"),
            payload={
                "draft_id": str(row.id),
                "expected_version": row.version,
                "expected_scheduled_for": (scheduled_for.isoformat()),
                "scheduled_by_user_id": str(self.actor_user_id),
            },
            commit=False,
        )

        self._audit(
            row.conversation_id,
            "reply_draft.scheduled",
            {
                "draft_id": str(row.id),
                "scheduled_for": (scheduled_for.isoformat()),
                "version": row.version,
            },
        )

        await self.db.commit()
        await self.db.refresh(row)

        return row

    async def cancel_scheduled_draft(
        self,
        draft_id: UUID,
        *,
        expected_version: int,
    ):
        row = await self._draft(
            draft_id,
            lock=True,
        )

        if row.status != "scheduled":
            raise HTTPException(
                status_code=409,
                detail="Draft is not scheduled",
            )

        if row.version != expected_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "draft_version_conflict",
                    "current_version": row.version,
                },
            )

        previous_scheduled_for = (
            row.scheduled_for.isoformat() if row.scheduled_for else None
        )

        row.status = "draft"
        row.scheduled_for = None
        row.scheduled_by_user_id = None
        row.version += 1

        self._audit(
            row.conversation_id,
            "reply_draft.schedule_cancelled",
            {
                "draft_id": str(row.id),
                "previous_scheduled_for": (previous_scheduled_for),
                "version": row.version,
            },
        )

        await self.db.commit()
        await self.db.refresh(row)

        return row

    async def execute_scheduled_draft_trigger(
        self,
        *,
        draft_id: UUID,
        expected_version: int,
        expected_scheduled_for: str,
    ) -> dict:
        row = await self._draft(
            draft_id,
            lock=True,
        )

        actual_scheduled_for = (
            row.scheduled_for.isoformat() if row.scheduled_for else None
        )

        if (
            row.version != expected_version
            or actual_scheduled_for != expected_scheduled_for
        ):
            return {
                "status": "superseded",
                "draft_id": str(row.id),
                "current_status": row.status,
                "current_version": row.version,
                "scheduled_for": actual_scheduled_for,
            }

        if row.status == "sent":
            return {
                "status": "sent",
                "draft_id": str(row.id),
                "message_id": (
                    str(row.sent_message_id) if row.sent_message_id else None
                ),
                "idempotent_replay": True,
            }

        if row.status not in {
            "scheduled",
            "sending",
        }:
            return {
                "status": "superseded",
                "draft_id": str(row.id),
                "current_status": row.status,
                "current_version": row.version,
                "scheduled_for": actual_scheduled_for,
            }

        if row.status == "scheduled":
            row.status = "sending"

            self._audit(
                row.conversation_id,
                "reply_draft.sending",
                {
                    "draft_id": str(row.id),
                    "scheduled_for": (actual_scheduled_for),
                    "version": row.version,
                },
            )

            # Persist the execution claim before crossing
            # the external side-effect boundary.
            await self.db.commit()
            await self.db.refresh(row)

        result = await CustomerServiceMessagingService(self.db).send_reply(
            workspace_id=self.workspace_id,
            actor_user_id=self.actor_user_id,
            conversation_id=row.conversation_id,
            payload=ReplySendRequest(
                body=row.body,
                idempotency_key=(f"reply-draft-{row.id}"),
            ),
        )

        # send_reply commits internally. Re-lock the draft
        # before recording the terminal product state.
        row = await self._draft(
            draft_id,
            lock=True,
        )

        actual_scheduled_for = (
            row.scheduled_for.isoformat() if row.scheduled_for else None
        )

        if (
            row.version != expected_version
            or actual_scheduled_for != expected_scheduled_for
        ):
            raise RuntimeError(
                "Scheduled reply generation changed after delivery claim"
            )

        if row.status == "sent":
            return {
                "status": "sent",
                "draft_id": str(row.id),
                "message_id": (
                    str(row.sent_message_id)
                    if row.sent_message_id
                    else result["message_id"]
                ),
                "idempotent_replay": True,
            }

        if row.status != "sending":
            raise RuntimeError("Scheduled reply left sending state during delivery")

        row.status = "sent"
        row.sent_message_id = UUID(result["message_id"])

        self._audit(
            row.conversation_id,
            "reply_draft.sent",
            {
                "draft_id": str(row.id),
                "message_id": result["message_id"],
                "scheduled_for": (actual_scheduled_for),
                "version": row.version,
                "idempotent_replay": bool(result.get("idempotent_replay")),
            },
        )

        await self.db.commit()
        await self.db.refresh(row)

        return {
            "status": "sent",
            "draft_id": str(row.id),
            "message_id": str(row.sent_message_id),
            "idempotent_replay": bool(result.get("idempotent_replay")),
        }

    async def validate_scheduled_draft_trigger(
        self,
        *,
        draft_id: UUID,
        expected_version: int,
        expected_scheduled_for: str,
    ) -> dict:
        row = await self._draft(
            draft_id,
            lock=True,
        )

        actual_scheduled_for = (
            row.scheduled_for.isoformat() if row.scheduled_for else None
        )

        if (
            row.status != "scheduled"
            or row.version != expected_version
            or actual_scheduled_for != expected_scheduled_for
        ):
            return {
                "status": "superseded",
                "draft_id": str(row.id),
                "current_status": row.status,
                "current_version": row.version,
                "scheduled_for": (actual_scheduled_for),
            }

        return {
            "status": "ready",
            "draft_id": str(row.id),
            "current_status": row.status,
            "current_version": row.version,
            "scheduled_for": (actual_scheduled_for),
        }

    async def send_draft(self, draft_id: UUID):
        row = await self._draft(draft_id, lock=True)
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Draft is not sendable")
        result = await CustomerServiceMessagingService(self.db).send_reply(
            workspace_id=self.workspace_id,
            actor_user_id=self.actor_user_id,
            conversation_id=row.conversation_id,
            payload=ReplySendRequest(
                body=row.body, idempotency_key=f"reply-draft-{row.id}"
            ),
        )
        row.status = "sent"
        row.sent_message_id = UUID(result["message_id"])
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def upsert_signature(
        self, *, user_id: UUID | None, payload: ReplySignatureWrite
    ):
        if user_id is not None:
            membership = await self.db.scalar(
                select(WorkspaceMembership.id).where(
                    WorkspaceMembership.workspace_id == self.workspace_id,
                    WorkspaceMembership.user_id == user_id,
                    WorkspaceMembership.status == "active",
                )
            )
            if membership is None:
                raise HTTPException(
                    status_code=404, detail="Workspace member not found"
                )
        scope_key = f"user:{user_id}" if user_id else "merchant"
        row = await self.db.scalar(
            select(CustomerServiceReplySignature).where(
                CustomerServiceReplySignature.workspace_id == self.workspace_id,
                CustomerServiceReplySignature.scope_key == scope_key,
            )
        )
        if row is None:
            row = CustomerServiceReplySignature(
                workspace_id=self.workspace_id,
                scope_key=scope_key,
                user_id=user_id,
                **payload.model_dump(),
            )
            self.db.add(row)
        else:
            for key, value in payload.model_dump().items():
                setattr(row, key, value)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list_signatures(self):
        return list(
            await self.db.scalars(
                select(CustomerServiceReplySignature)
                .where(CustomerServiceReplySignature.workspace_id == self.workspace_id)
                .order_by(CustomerServiceReplySignature.scope_key)
            )
        )

    async def update_customer_custom_fields(self, customer_id: UUID, values: dict):
        row = await self.db.scalar(
            select(Customer).where(
                Customer.user_id == self.workspace_id, Customer.id == customer_id
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        custom_fields = dict(row.custom_fields or {})
        for key, value in values.items():
            if value is None:
                custom_fields.pop(key, None)
            else:
                custom_fields[key] = value
        row.custom_fields = custom_fields
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def productivity(self, *, days: int = 30):
        # The report uses durable audit and assignment truth rather than ephemeral presence.
        since = datetime.now(timezone.utc) - timedelta(days=days)
        reply_rows = (
            await self.db.execute(
                select(
                    CustomerServiceAuditLog.actor_id,
                    func.count(CustomerServiceAuditLog.id),
                )
                .where(
                    CustomerServiceAuditLog.user_id == self.workspace_id,
                    CustomerServiceAuditLog.created_at >= since,
                    CustomerServiceAuditLog.action.in_(
                        ["suggested_action.executed", "autopilot.reply_sent"]
                    ),
                )
                .group_by(CustomerServiceAuditLog.actor_id)
            )
        ).all()
        assignment_rows = (
            await self.db.execute(
                select(TicketAssignment.assigned_to, func.count(TicketAssignment.id))
                .where(
                    TicketAssignment.user_id == self.workspace_id,
                    TicketAssignment.created_at >= since,
                )
                .group_by(TicketAssignment.assigned_to)
            )
        ).all()
        metrics: dict[str, dict] = {}
        for actor_id, count in reply_rows:
            key = str(actor_id) if actor_id else "automation"
            metrics.setdefault(key, {"actor_id": key, "replies": 0, "assignments": 0})[
                "replies"
            ] = count
        for actor_id, count in assignment_rows:
            key = str(actor_id) if actor_id else "unassigned"
            metrics.setdefault(key, {"actor_id": key, "replies": 0, "assignments": 0})[
                "assignments"
            ] = count
        return {"period_days": days, "agents": list(metrics.values())}

    async def _conversation(self, conversation_id: UUID, *, lock: bool = False):
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == self.workspace_id,
            Conversation.merged_into_id.is_(None),
        )
        if lock:
            statement = statement.with_for_update()
        row = await self.db.scalar(statement)
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return row

    async def _draft(self, draft_id: UUID, *, lock: bool = False):
        statement = select(CustomerServiceReplyDraft).where(
            CustomerServiceReplyDraft.id == draft_id,
            CustomerServiceReplyDraft.workspace_id == self.workspace_id,
        )
        if lock:
            statement = statement.with_for_update()
        row = await self.db.scalar(statement)
        if row is None:
            raise HTTPException(status_code=404, detail="Draft not found")
        return row

    def _audit(self, conversation_id: UUID, action: str, meta: dict):
        self.db.add(
            CustomerServiceAuditLog(
                user_id=self.workspace_id,
                actor_id=self.actor_user_id,
                entity_type="conversation",
                entity_id=conversation_id,
                action=action,
                meta={"conversation_id": str(conversation_id), **meta},
            )
        )
