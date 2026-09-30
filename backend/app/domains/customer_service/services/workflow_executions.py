from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models.tickets import Ticket
from app.domains.customer_service.realtime.publisher import (
    CustomerServiceRealtimePublisher,
)
from app.domains.customer_service.repositories.conversations import (
    ConversationRepository,
)
from app.domains.customer_service.repositories.workflow_executions import (
    CustomerServiceWorkflowExecutionRepository,
)
from app.domains.customer_service.repositories.workflow_templates import (
    WorkflowTemplateRepository,
)
from app.platform.jobs.service import JobService
from app.workflow_operations.snapshots.replay import WorkflowReplayService
from app.workflow_operations.snapshots.service import WorkflowSnapshotService
from app.workflow_operations.timeline.service import WorkflowTimelineService
from app.workflow_operations.waits.service import WorkflowWaitService


class CustomerServiceWorkflowExecutionService:
    def __init__(self, db: AsyncSession):
        self.repo = CustomerServiceWorkflowExecutionRepository(db)

    async def run_template_for_conversation(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        template_id: UUID,
        message: str | None = None,
    ) -> dict:
        conversation = await ConversationRepository(self.repo.db).get_detail(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        template = await WorkflowTemplateRepository(self.repo.db).get_for_user(
            user_id=user_id,
            template_id=template_id,
        )

        if template is None:
            raise HTTPException(status_code=404, detail="Workflow template not found")

        if template.status != "published":
            raise HTTPException(
                status_code=409,
                detail="Only published workflow templates can be run from a conversation",
            )

        workflow = template.workflow_json or {}
        latest_message = None

        if getattr(conversation, "messages", None):
            latest_message = sorted(
                conversation.messages,
                key=lambda item: item.created_at,
                reverse=True,
            )[0]

        run_message = (
            message
            or getattr(latest_message, "body", None)
            or conversation.subject
            or "Run customer-service workflow"
        )

        ticket_id = await self.repo.db.scalar(
            select(Ticket.id).where(
                Ticket.user_id == user_id,
                Ticket.conversation_id == conversation.id,
            )
        )

        event_payload = {
            "conversation_id": str(conversation.id),
            "ticket_id": str(ticket_id) if ticket_id else None,
            "customer_id": str(conversation.customer_id),
            "channel": conversation.channel,
            "subject": conversation.subject,
            "body": run_message,
        }

        job = await JobService(self.repo.db).enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload=jsonable_encoder(
                {
                    "workflow": workflow,
                    "message": run_message,
                    "thread_id": str(conversation.id),
                    "extras": {
                        "customer_service": True,
                        "manual_trigger": True,
                        "event": {
                            "event_type": "conversation.workflow_template.manual_run",
                            "source": "customer_service.inbox",
                            "payload": event_payload,
                            "meta": {
                                "template_id": str(template.id),
                                "template_name": template.name,
                            },
                        },
                        "template": {
                            "id": str(template.id),
                            "name": template.name,
                            "category": template.category,
                            "scope": template.scope,
                        },
                    },
                }
            ),
            max_attempts=3,
        )

        await CustomerServiceRealtimePublisher().publish_workflow_started(
            user_id=user_id,
            conversation_id=conversation.id,
            job_id=job.id,
            payload={
                "template_id": str(template.id),
                "template_name": template.name,
                "ticket_id": str(ticket_id) if ticket_id else None,
                "source": "manual_template_run",
            },
        )

        return await self.get(user_id=user_id, job_id=job.id)

    async def list(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID | None = None,
        ticket_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        jobs = await self.repo.list_for_user(
            user_id=user_id,
            conversation_id=conversation_id,
            ticket_id=ticket_id,
            limit=limit,
            offset=offset,
        )

        executions = [self._normalize(job) for job in jobs]
        handed_over = await self._handed_over_runs(
            [e["workflow_run_id"] for e in executions if e["workflow_run_id"]]
        )
        waiting = await self._waiting_approval_runs(
            [e["workflow_run_id"] for e in executions if e["workflow_run_id"]]
        )
        for execution in executions:
            execution["handed_over"] = str(execution["workflow_run_id"]) in handed_over
            execution["waiting_approval"] = str(execution["workflow_run_id"]) in waiting
        return executions

    async def _waiting_approval_runs(self, run_ids: list) -> set[str]:
        # The job "succeeds" when its run pauses for an approval; the case is
        # still waiting on the team, not answered.
        if not run_ids:
            return set()
        result = await self.repo.db.execute(
            text(
                """
                SELECT DISTINCT workflow_run_id FROM workflow_waits
                WHERE workflow_run_id = ANY(:ids)
                  AND wait_type = 'approval' AND status = 'waiting'
                """
            ),
            {"ids": [str(r) for r in run_ids]},
        )
        return set(result.scalars().all())

    async def _handed_over_runs(self, run_ids: list) -> set[str]:
        # A run "succeeds" even when a step gave up and asked for a person
        # (AI provider down, fallback reply); the inbox must not call that answered.
        if not run_ids:
            return set()
        result = await self.repo.db.execute(
            text(
                """
                SELECT DISTINCT workflow_run_id::text FROM workflow_run_events
                WHERE workflow_run_id::text = ANY(:ids)
                  AND event->'meta'->>'handoff_required' = 'true'
                """
            ),
            {"ids": [str(r) for r in run_ids]},
        )
        return set(result.scalars().all())

    async def get(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
    ) -> dict:
        job = await self.repo.get_for_user(
            user_id=user_id,
            job_id=job_id,
        )

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow execution not found",
            )

        return self._normalize(job)

    async def list_approvals(self, *, user_id: UUID, status: str = "waiting"):
        waits = await WorkflowWaitService(self.repo.db).list_for_user(
            user_id=user_id,
            status=status,
        )
        return [wait for wait in waits if wait.wait_type == "approval"]

    async def decide_approval(
        self, *, user_id: UUID, wait_id: UUID, approved: bool
    ) -> dict:
        service = WorkflowWaitService(self.repo.db)
        wait = await service.get_for_user(user_id=user_id, wait_id=wait_id)
        if wait.wait_type != "approval":
            raise HTTPException(status_code=422, detail="Wait is not an approval")
        result = (
            await service.approve(user_id=user_id, wait_id=wait_id)
            if approved
            else await service.reject(user_id=user_id, wait_id=wait_id)
        )
        return {
            "wait_id": str(result["wait"].id),
            "status": result["wait"].status,
            "workflow_run_id": result["wait"].workflow_run_id,
            "resume_job_id": (
                str(result["resume_job"].id) if result.get("resume_job") else None
            ),
            "approved": approved,
        }

    async def timeline(self, *, user_id: UUID, job_id: UUID):
        execution = await self.get(user_id=user_id, job_id=job_id)
        run_id = execution.get("workflow_run_id")
        if not run_id:
            raise HTTPException(
                status_code=409,
                detail="Workflow execution has not produced a runtime run yet",
            )
        return await WorkflowTimelineService(self.repo.db).get_timeline(
            workflow_run_id=UUID(str(run_id)),
            user_id=user_id,
        )

    async def snapshots(self, *, user_id: UUID, job_id: UUID):
        execution = await self.get(user_id=user_id, job_id=job_id)
        run_id = execution.get("workflow_run_id")
        if not run_id:
            raise HTTPException(
                status_code=409,
                detail="Workflow execution has not produced a runtime run yet",
            )
        return await WorkflowSnapshotService(self.repo.db).list_for_run(
            workflow_run_id=UUID(str(run_id)),
            user_id=user_id,
        )

    async def replay_snapshot(self, *, user_id: UUID, snapshot_id: UUID):
        result = await WorkflowReplayService(self.repo.db).create_replay_job(
            user_id=user_id,
            snapshot_id=snapshot_id,
        )
        return {
            "snapshot_id": str(result["snapshot"].id),
            "workflow_run_id": str(result["snapshot"].workflow_run_id),
            "job_id": str(result["job"].id),
            "status": result["job"].status,
        }

    def _normalize(self, job) -> dict:
        payload = job.payload or {}
        result = job.result or None
        extras = payload.get("extras") or {}
        event = extras.get("event") or {}
        event_payload = event.get("payload") or {}
        subscription = extras.get("subscription") or {}
        workflow = payload.get("workflow") or {}

        workflow_run_id = None
        if isinstance(result, dict):
            workflow_run_id = (
                result.get("workflow_run_id")
                or result.get("run_id")
                or (result.get("meta") or {}).get("workflow_run_id")
            )

        return {
            "job_id": job.id,
            "workflow_run_id": workflow_run_id,
            "user_id": job.user_id,
            "status": job.status,
            "job_type": job.job_type,
            "template_name": workflow.get("name"),
            "subscription_name": subscription.get("name"),
            "workflow_version": extras.get("workflow_version"),
            "trigger_event_type": event.get("event_type"),
            "conversation_id": event_payload.get("conversation_id"),
            "ticket_id": event_payload.get("ticket_id"),
            "customer_id": event_payload.get("customer_id"),
            "channel": event_payload.get("channel"),
            "message": extras.get("customer_message") or payload.get("message"),
            "workflow_name": (
                "Order request review"
                if extras.get("support_review")
                else workflow.get("name")
            ),
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "error_message": job.error_message,
            "payload": payload,
            "result": result,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }
