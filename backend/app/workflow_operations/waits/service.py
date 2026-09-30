from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveRepairExecutionRecord,
)
from app.platform.jobs.service import JobService
from app.workflow_operations.waits.repository import WorkflowWaitRepository


class WorkflowWaitService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WorkflowWaitRepository(db)
        self.jobs = JobService(db)

    async def create(self, *, user_id, payload):
        expires_at = (
            self._ensure_aware(payload.expires_at) if payload.expires_at else None
        )

        return await self.repo.create(
            user_id=user_id,
            workflow_run_id=payload.workflow_run_id,
            node_id=payload.node_id,
            wait_type=payload.wait_type,
            payload=payload.payload,
            expires_at=expires_at,
        )

    async def get_for_user(self, *, user_id, wait_id: UUID):
        wait = await self.repo.get_for_user(
            user_id=user_id,
            wait_id=wait_id,
        )

        if wait is None:
            raise HTTPException(status_code=404, detail="Workflow wait not found")

        return wait

    async def list_for_user(
        self,
        *,
        user_id,
        status: str | None = None,
        workflow_run_id: str | None = None,
    ):
        return await self.repo.list_for_user(
            user_id=user_id,
            status=status,
            workflow_run_id=workflow_run_id,
        )

    async def resolve_waits_for_completed_run(
        self,
        *,
        user_id,
        workflow_run_id: str,
        resolution: dict,
    ):
        """
        Reconcile durable waits after a synchronous workflow resume succeeds.

        The normal wait endpoints resolve first and enqueue workflow.resume.
        The generic synchronous resume route executes first, then calls this
        method so a failed execution does not consume the human decision.
        """
        waits = await self.repo.list_waiting_for_run(
            user_id=user_id,
            workflow_run_id=str(workflow_run_id),
        )

        resolved = []

        for wait in waits:
            saved = await self.repo.resolve_waiting(
                user_id=user_id,
                wait_id=wait.id,
                resolution=resolution or {},
            )

            if saved is not None:
                resolved.append(saved)

        return resolved

    async def resolve(
        self, *, user_id, wait_id: UUID, resolution: dict, resume: bool = True
    ):
        saved = await self.repo.resolve_waiting(
            user_id=user_id,
            wait_id=wait_id,
            resolution=resolution or {},
        )

        if saved is None:
            wait = await self.repo.get_for_user(
                user_id=user_id,
                wait_id=wait_id,
            )

            if wait is None:
                raise HTTPException(status_code=404, detail="Workflow wait not found")

            raise HTTPException(
                status_code=409, detail=f"Wait is already {wait.status}"
            )

        resume_job = None

        if resume:
            resume_job = await self.jobs.enqueue(
                user_id=user_id,
                job_type="workflow.resume",
                payload={
                    "workflow_run_id": saved.workflow_run_id,
                    "extras": await self._repair_resume_extras(
                        user_id=saved.user_id,
                        workflow_run_id=(saved.workflow_run_id),
                    ),
                    "input": {
                        "wait_id": str(saved.id),
                        "wait_type": saved.wait_type,
                        "node_id": saved.node_id,
                        "resolution": saved.resolution or {},
                    },
                },
                max_attempts=3,
            )

        return {
            "wait": saved,
            "resume_job_id": str(resume_job.id) if resume_job else None,
        }

    async def approve(self, *, user_id, wait_id):
        result = await self.resolve(
            user_id=user_id,
            wait_id=wait_id,
            resolution={
                "approved": True,
                "action": "approved",
            },
            resume=False,
        )

        if not result.get("resume_job"):
            wait = result["wait"]
            resume_job = await self.jobs.enqueue(
                user_id=user_id,
                job_type="workflow.resume",
                payload={
                    "workflow_run_id": wait.workflow_run_id,
                    "extras": await self._repair_resume_extras(
                        user_id=wait.user_id,
                        workflow_run_id=(wait.workflow_run_id),
                    ),
                    "input": {
                        "approved": True,
                        "wait_id": str(wait.id),
                        "resolution": result.get("resolution") or wait.resolution or {},
                    },
                },
            )
            result["resume_job"] = resume_job

        return result

    async def reject(self, *, user_id, wait_id):
        result = await self.resolve(
            user_id=user_id,
            wait_id=wait_id,
            resolution={
                "approved": False,
                "action": "rejected",
            },
            resume=False,
        )

        if not result.get("resume_job"):
            wait = result["wait"]
            resume_job = await self.jobs.enqueue(
                user_id=user_id,
                job_type="workflow.resume",
                payload={
                    "workflow_run_id": wait.workflow_run_id,
                    "extras": await self._repair_resume_extras(
                        user_id=wait.user_id,
                        workflow_run_id=(wait.workflow_run_id),
                    ),
                    "input": {
                        "approved": False,
                        "wait_id": str(wait.id),
                        "resolution": result.get("resolution") or wait.resolution or {},
                    },
                },
            )
            result["resume_job"] = resume_job

        return result

    async def expire(self, *, wait):
        if wait.status not in {"waiting", "processing"}:
            return wait

        wait.status = "expired"
        wait.resolution = {
            "expired": True,
            "reason": "expires_at reached",
        }
        wait.resolved_at = datetime.now(timezone.utc)

        saved = await self.repo.save(wait)

        await self.jobs.enqueue(
            user_id=wait.user_id,
            job_type="workflow.resume",
            payload={
                "workflow_run_id": wait.workflow_run_id,
                "extras": await self._repair_resume_extras(
                    user_id=wait.user_id,
                    workflow_run_id=(wait.workflow_run_id),
                ),
                "input": {
                    "wait_id": str(wait.id),
                    "wait_type": wait.wait_type,
                    "node_id": wait.node_id,
                    "expired": True,
                    "resolution": saved.resolution or {},
                },
            },
            max_attempts=3,
        )

        return saved

    async def _repair_resume_extras(
        self,
        *,
        user_id,
        workflow_run_id: str,
    ) -> dict:
        """
        Resolve objective-repair lineage from durable repair
        persistence for a workflow.resume job.

        Generic workflow runs return an empty extras object.
        Lineage is never reconstructed from mutable wait payloads
        or workflow state.
        """

        normalized_run_id = str(workflow_run_id or "").strip()

        if not normalized_run_id:
            return {}

        result = await self.db.execute(
            select(ObjectiveRepairExecutionRecord)
            .where(
                ObjectiveRepairExecutionRecord.user_id == user_id,
                ObjectiveRepairExecutionRecord.workflow_run_id == normalized_run_id,
            )
            .order_by(ObjectiveRepairExecutionRecord.created_at.desc())
            .limit(2)
        )

        repairs = list(result.scalars().all())

        if not repairs:
            return {}

        if len(repairs) > 1:
            raise RuntimeError(
                "Multiple objective repair executions share the same workflow_run_id"
            )

        repair = repairs[0]

        return {
            "customer_service": True,
            "objective_repair": {
                "repair_execution_id": str(repair.id),
            },
        }

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)
