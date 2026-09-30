from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import (
    Conversation,
    ConversationMessage,
    ConversationTag,
    CustomerServiceAuditLog,
    CustomerServiceConversationInsight,
    CustomerServiceQualityReview,
    CustomerServiceSuggestedAction,
    SLAViolation,
    Ticket,
    TicketAssignment,
)
from app.domains.customer_service.services.workflow_executions import (
    CustomerServiceWorkflowExecutionService,
)


class ConversationTimelineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _source_limit(self, limit: int) -> int:
        # Each timeline source is individually bounded before merge/sort.
        # This prevents one high-volume source, such as messages or audit logs,
        # from loading unbounded rows only to be trimmed by the final limit.
        return max(1, min(limit, 500))

    async def get_timeline(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        limit: int = 100,
    ) -> list[dict]:
        conversation = await self._get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        ticket = await self._get_ticket(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        events: list[dict] = []
        source_limit = self._source_limit(limit)

        events.extend(await self._message_events(conversation_id, limit=source_limit))
        events.extend(
            await self._tag_events(user_id, conversation_id, limit=source_limit)
        )
        events.extend(
            await self._insight_events(user_id, conversation_id, limit=source_limit)
        )
        events.extend(
            await self._suggested_action_events(
                user_id, conversation_id, limit=source_limit
            )
        )
        events.extend(
            await self._quality_review_events(
                user_id, conversation_id, limit=source_limit
            )
        )

        if ticket is not None:
            events.extend(
                await self._assignment_events(user_id, ticket.id, limit=source_limit)
            )
            events.extend(
                await self._sla_events(user_id, ticket.id, limit=source_limit)
            )

        events.extend(
            await self._audit_events(
                user_id=user_id,
                conversation_id=conversation_id,
                ticket_id=ticket.id if ticket is not None else None,
                limit=source_limit,
            )
        )

        events.extend(
            await self._workflow_execution_events(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=source_limit,
            )
        )

        events.sort(key=lambda event: event["timestamp"], reverse=True)

        return events[:limit]

    async def _get_conversation(self, *, user_id: UUID, conversation_id: UUID):
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.id == conversation_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_ticket(self, *, user_id: UUID, conversation_id: UUID):
        result = await self.db.execute(
            select(Ticket).where(
                Ticket.user_id == user_id,
                Ticket.conversation_id == conversation_id,
            )
        )
        return result.scalar_one_or_none()

    async def _message_events(self, conversation_id: UUID, *, limit: int) -> list[dict]:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )

        events = []
        for message in result.scalars().all():
            sender = self._value(message.sender_type)
            event_type = "internal_note" if sender == "internal_note" else "message"
            title = (
                "Internal note"
                if sender == "internal_note"
                else f"{sender.title()} message"
            )

            events.append(
                self._event(
                    type=event_type,
                    timestamp=message.created_at,
                    title=title,
                    description=message.body,
                    entity_id=message.id,
                    entity_type="conversation_message",
                    metadata={
                        "sender_type": sender,
                        "conversation_id": str(message.conversation_id),
                        "meta": message.meta,
                    },
                )
            )

        return events

    async def _tag_events(
        self, user_id: UUID, conversation_id: UUID, *, limit: int
    ) -> list[dict]:
        result = await self.db.execute(
            select(ConversationTag)
            .where(
                ConversationTag.user_id == user_id,
                ConversationTag.conversation_id == conversation_id,
            )
            .order_by(ConversationTag.created_at.desc())
            .limit(limit)
        )

        return [
            self._event(
                type="tag_added",
                timestamp=tag.created_at,
                title="Tag added",
                description=tag.name,
                entity_id=tag.id,
                entity_type="conversation_tag",
                metadata={
                    "name": tag.name,
                    "conversation_id": str(tag.conversation_id),
                },
            )
            for tag in result.scalars().all()
        ]

    async def _assignment_events(
        self, user_id: UUID, ticket_id: UUID, *, limit: int
    ) -> list[dict]:
        result = await self.db.execute(
            select(TicketAssignment)
            .where(
                TicketAssignment.user_id == user_id,
                TicketAssignment.ticket_id == ticket_id,
            )
            .order_by(TicketAssignment.created_at.desc())
            .limit(limit)
        )

        events = []
        for assignment in result.scalars().all():
            events.append(
                self._event(
                    type="ticket_assigned",
                    timestamp=assignment.created_at,
                    title="Ticket assigned",
                    description=(
                        f"Assigned to {assignment.assigned_to}"
                        if assignment.assigned_to is not None
                        else "Ticket assignment cleared"
                    ),
                    actor_id=assignment.assigned_by,
                    entity_id=assignment.id,
                    entity_type="ticket_assignment",
                    metadata={
                        "ticket_id": str(assignment.ticket_id),
                        "assigned_to": str(assignment.assigned_to)
                        if assignment.assigned_to is not None
                        else None,
                        "is_active": assignment.is_active,
                        "meta": assignment.meta,
                    },
                )
            )

        return events

    async def _sla_events(
        self, user_id: UUID, ticket_id: UUID, *, limit: int
    ) -> list[dict]:
        result = await self.db.execute(
            select(SLAViolation)
            .where(
                SLAViolation.user_id == user_id,
                SLAViolation.ticket_id == ticket_id,
            )
            .order_by(SLAViolation.created_at.desc())
            .limit(limit)
        )

        events = []
        for violation in result.scalars().all():
            target_type = self._value(violation.target_type)
            status = self._value(violation.status)

            if violation.breached_at is not None:
                events.append(
                    self._event(
                        type="sla_breached",
                        timestamp=violation.breached_at,
                        title="SLA breached",
                        description=target_type,
                        entity_id=violation.id,
                        entity_type="sla_violation",
                        metadata={
                            "ticket_id": str(violation.ticket_id),
                            "target_type": target_type,
                            "status": status,
                            "due_at": violation.due_at.isoformat(),
                        },
                    )
                )

            events.append(
                self._event(
                    type="sla_target",
                    timestamp=violation.created_at,
                    title="SLA target created",
                    description=target_type,
                    entity_id=violation.id,
                    entity_type="sla_violation",
                    metadata={
                        "ticket_id": str(violation.ticket_id),
                        "target_type": target_type,
                        "status": status,
                        "due_at": violation.due_at.isoformat(),
                        "breached_at": violation.breached_at.isoformat()
                        if violation.breached_at is not None
                        else None,
                    },
                )
            )

        return events

    async def _insight_events(
        self, user_id: UUID, conversation_id: UUID, *, limit: int
    ) -> list[dict]:
        result = await self.db.execute(
            select(CustomerServiceConversationInsight)
            .where(
                CustomerServiceConversationInsight.user_id == user_id,
                CustomerServiceConversationInsight.conversation_id == conversation_id,
            )
            .order_by(CustomerServiceConversationInsight.created_at.desc())
            .limit(limit)
        )

        return [
            self._event(
                type="insight_generated",
                timestamp=insight.created_at,
                title="Conversation intelligence generated",
                description=insight.intent,
                entity_id=insight.id,
                entity_type="conversation_insight",
                metadata={
                    "sentiment": insight.sentiment,
                    "intent": insight.intent,
                    "urgency": insight.urgency,
                    "confidence": insight.confidence,
                    "language": insight.language,
                    "source": insight.source,
                    "model_version": insight.model_version,
                    "fallback_reason": insight.fallback_reason,
                    "summary": insight.summary,
                    "entities": insight.entities,
                    "risks": insight.risks,
                    "opportunities": insight.opportunities,
                },
            )
            for insight in result.scalars().all()
        ]

    async def _suggested_action_events(
        self,
        user_id: UUID,
        conversation_id: UUID,
        *,
        limit: int,
    ) -> list[dict]:
        result = await self.db.execute(
            select(CustomerServiceSuggestedAction)
            .where(
                CustomerServiceSuggestedAction.user_id == user_id,
                CustomerServiceSuggestedAction.conversation_id == conversation_id,
            )
            .order_by(CustomerServiceSuggestedAction.created_at.desc())
            .limit(limit)
        )

        return [
            self._event(
                type="suggested_action",
                timestamp=action.created_at,
                title=action.title,
                description=action.description,
                entity_id=action.id,
                entity_type="suggested_action",
                metadata={
                    "action_type": action.action_type,
                    "status": action.status,
                    "confidence": action.confidence,
                    "source": action.source,
                    "payload": action.payload,
                    "updated_at": action.updated_at.isoformat()
                    if action.updated_at is not None
                    else None,
                },
            )
            for action in result.scalars().all()
        ]

    async def _quality_review_events(
        self,
        user_id: UUID,
        conversation_id: UUID,
        *,
        limit: int,
    ) -> list[dict]:
        result = await self.db.execute(
            select(CustomerServiceQualityReview)
            .where(
                CustomerServiceQualityReview.user_id == user_id,
                CustomerServiceQualityReview.conversation_id == conversation_id,
            )
            .order_by(CustomerServiceQualityReview.created_at.desc())
            .limit(limit)
        )

        return [
            self._event(
                type="quality_review",
                timestamp=review.created_at,
                title="Quality review completed",
                description=f"Score {review.overall_score}",
                entity_id=review.id,
                entity_type="quality_review",
                metadata={
                    "overall_score": review.overall_score,
                    "scores": review.scores,
                    "issues": review.issues,
                    "recommendations": review.recommendations,
                    "reviewer_type": review.reviewer_type,
                    "review_type": review.review_type,
                    "outcome": review.outcome,
                },
            )
            for review in result.scalars().all()
        ]

    async def _audit_events(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        ticket_id: UUID | None,
        limit: int,
    ) -> list[dict]:
        entity_ids = [conversation_id]
        if ticket_id is not None:
            entity_ids.append(ticket_id)

        result = await self.db.execute(
            select(CustomerServiceAuditLog)
            .where(
                CustomerServiceAuditLog.user_id == user_id,
                or_(
                    CustomerServiceAuditLog.entity_id.in_(entity_ids),
                    CustomerServiceAuditLog.meta["conversation_id"].astext
                    == str(conversation_id),
                ),
            )
            .order_by(CustomerServiceAuditLog.created_at.desc())
            .limit(limit)
        )

        return [
            self._event(
                type="audit_log",
                timestamp=log.created_at,
                title=log.action,
                description=log.message,
                actor_id=log.actor_id,
                entity_id=log.id,
                entity_type="audit_log",
                metadata={
                    "audit_entity_type": log.entity_type,
                    "audit_entity_id": str(log.entity_id)
                    if log.entity_id is not None
                    else None,
                    "meta": log.meta,
                },
            )
            for log in result.scalars().all()
        ]

    async def _workflow_execution_events(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        limit: int,
    ) -> list[dict]:
        executions = await CustomerServiceWorkflowExecutionService(self.db).list(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit,
            offset=0,
        )

        events = []
        for execution in executions:
            events.append(
                self._event(
                    type="workflow_execution",
                    timestamp=execution["created_at"],
                    title=execution.get("subscription_name")
                    or execution.get("workflow_name")
                    or execution.get("template_name")
                    or "Workflow execution",
                    description=execution.get("message"),
                    entity_id=execution.get("job_id"),
                    entity_type="workflow_execution",
                    metadata={
                        "job_id": str(execution.get("job_id")),
                        "workflow_run_id": str(execution.get("workflow_run_id"))
                        if execution.get("workflow_run_id") is not None
                        else None,
                        "status": execution.get("status"),
                        "job_type": execution.get("job_type"),
                        "template_name": execution.get("template_name"),
                        "subscription_name": execution.get("subscription_name"),
                        "workflow_version": execution.get("workflow_version"),
                        "handed_over": execution.get("handed_over"),
                        "trigger_event_type": execution.get("trigger_event_type"),
                        "ticket_id": execution.get("ticket_id"),
                        "customer_id": execution.get("customer_id"),
                        "channel": execution.get("channel"),
                        "attempts": execution.get("attempts"),
                        "max_attempts": execution.get("max_attempts"),
                        "error_message": execution.get("error_message"),
                    },
                )
            )

        return events

    def _event(
        self,
        *,
        type: str,
        timestamp,
        title: str,
        description: str | None = None,
        actor_id: UUID | None = None,
        entity_id: UUID | None = None,
        entity_type: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        return {
            "type": type,
            "timestamp": timestamp,
            "title": title,
            "description": description,
            "actor_id": actor_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "metadata": metadata or {},
        }

    def _value(self, value) -> str:
        return getattr(value, "value", str(value))
