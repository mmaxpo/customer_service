from __future__ import annotations

from uuid import UUID

from app.domains.customer_service.realtime import events
from app.platform.realtime import realtime_publisher


class CustomerServiceRealtimePublisher:
    async def publish_agent_presence_changed(self, *, user_id: UUID, agent) -> object:
        return await realtime_publisher.publish(
            user_id=user_id,
            type=events.AGENT_PRESENCE_CHANGED,
            scope=events.CUSTOMER_SERVICE_SCOPE,
            entity_type="agent",
            entity_id=agent.id,
            payload={
                "agent_id": str(agent.id),
                "agent_user_id": str(agent.agent_user_id),
                "presence": agent.availability,
                "availability_source": getattr(agent, "availability_source", "manual"),
            },
        )

    async def publish_conversation_created(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        payload: dict | None = None,
    ):
        return await realtime_publisher.publish(
            user_id=user_id,
            type=events.CONVERSATION_CREATED,
            scope=events.CUSTOMER_SERVICE_SCOPE,
            entity_type="conversation",
            entity_id=conversation_id,
            payload={
                "conversation_id": str(conversation_id),
                **(payload or {}),
            },
        )

    async def publish_message_created(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        sender_type: str,
        preview: str | None = None,
        payload: dict | None = None,
    ):
        event_type = (
            events.AI_REPLY_CREATED if sender_type == "ai" else events.MESSAGE_CREATED
        )

        return await realtime_publisher.publish(
            user_id=user_id,
            type=event_type,
            scope=events.CUSTOMER_SERVICE_SCOPE,
            entity_type="conversation",
            entity_id=conversation_id,
            payload={
                "conversation_id": str(conversation_id),
                "message_id": str(message_id),
                "sender_type": sender_type,
                "preview": preview,
                **(payload or {}),
            },
        )

    async def publish_workflow_started(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | str | None,
        job_id: UUID | str | None = None,
        workflow_run_id: UUID | str | None = None,
        payload: dict | None = None,
    ):
        return await self._publish_workflow_event(
            user_id=user_id,
            event_type=events.WORKFLOW_STARTED,
            conversation_id=conversation_id,
            job_id=job_id,
            workflow_run_id=workflow_run_id,
            payload=payload,
        )

    async def publish_workflow_succeeded(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | str | None,
        job_id: UUID | str | None = None,
        workflow_run_id: UUID | str | None = None,
        payload: dict | None = None,
    ):
        return await self._publish_workflow_event(
            user_id=user_id,
            event_type=events.WORKFLOW_SUCCEEDED,
            conversation_id=conversation_id,
            job_id=job_id,
            workflow_run_id=workflow_run_id,
            payload=payload,
        )

    async def publish_workflow_failed(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | str | None,
        job_id: UUID | str | None = None,
        workflow_run_id: UUID | str | None = None,
        payload: dict | None = None,
    ):
        return await self._publish_workflow_event(
            user_id=user_id,
            event_type=events.WORKFLOW_FAILED,
            conversation_id=conversation_id,
            job_id=job_id,
            workflow_run_id=workflow_run_id,
            payload=payload,
        )

    async def publish_workflow_paused(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | str | None,
        job_id: UUID | str | None = None,
        workflow_run_id: UUID | str | None = None,
        payload: dict | None = None,
    ):
        return await self._publish_workflow_event(
            user_id=user_id,
            event_type=events.WORKFLOW_PAUSED,
            conversation_id=conversation_id,
            job_id=job_id,
            workflow_run_id=workflow_run_id,
            payload=payload,
        )

    async def publish_approval_required(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | str | None,
        job_id: UUID | str | None = None,
        workflow_run_id: UUID | str | None = None,
        payload: dict | None = None,
    ):
        return await self._publish_workflow_event(
            user_id=user_id,
            event_type=events.APPROVAL_REQUIRED,
            conversation_id=conversation_id,
            job_id=job_id,
            workflow_run_id=workflow_run_id,
            payload=payload,
        )

    async def publish_sla_updated(
        self,
        *,
        user_id: UUID,
        ticket_id: UUID | str,
        conversation_id: UUID | str | None = None,
        status: str,
        payload: dict | None = None,
    ):
        return await realtime_publisher.publish(
            user_id=user_id,
            type=events.SLA_UPDATED,
            scope=events.CUSTOMER_SERVICE_SCOPE,
            entity_type="ticket",
            entity_id=ticket_id,
            payload={
                "ticket_id": str(ticket_id),
                "conversation_id": str(conversation_id) if conversation_id else None,
                "status": status,
                **(payload or {}),
            },
        )

    async def publish_shopify_action_completed(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | str | None = None,
        order_ref: str | None = None,
        action: str,
        status: str | None = None,
        payload: dict | None = None,
    ):
        return await realtime_publisher.publish(
            user_id=user_id,
            type=events.SHOPIFY_ACTION_COMPLETED,
            scope=events.CUSTOMER_SERVICE_SCOPE,
            entity_type="shopify_action",
            entity_id=conversation_id,
            payload={
                "conversation_id": str(conversation_id) if conversation_id else None,
                "order_ref": order_ref,
                "action": action,
                "status": status,
                **(payload or {}),
            },
        )

    async def _publish_workflow_event(
        self,
        *,
        user_id: UUID,
        event_type: str,
        conversation_id: UUID | str | None,
        job_id: UUID | str | None = None,
        workflow_run_id: UUID | str | None = None,
        payload: dict | None = None,
    ):
        entity_id = conversation_id or workflow_run_id or job_id

        return await realtime_publisher.publish(
            user_id=user_id,
            type=event_type,
            scope=events.CUSTOMER_SERVICE_SCOPE,
            entity_type="conversation" if conversation_id else "workflow",
            entity_id=entity_id,
            payload={
                "conversation_id": str(conversation_id) if conversation_id else None,
                "job_id": str(job_id) if job_id else None,
                "workflow_run_id": str(workflow_run_id) if workflow_run_id else None,
                **(payload or {}),
            },
        )
