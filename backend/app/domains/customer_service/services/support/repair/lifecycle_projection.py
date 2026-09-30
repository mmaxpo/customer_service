from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveRepairExecutionRecord,
    PlatformJob,
)
from app.platform.jobs.repository import JobRepository
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED,
    OBJECTIVE_REPAIR_EXECUTION_TERMINAL_STATUSES,
    ObjectiveRepairExecutionConflictError,
    ObjectiveRepairExecutionNotFoundError,
    ObjectiveRepairExecutionRepository,
    ObjectiveRepairExecutionService,
)


class CustomerSupportRepairLifecycleProjectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class CustomerSupportRepairLifecycleProjectionResult:
    repair_execution: ObjectiveRepairExecutionRecord | None
    projected: bool
    reason: str
    workflow_job_id: UUID


class CustomerSupportRepairLifecycleProjector:
    """
    Project durable workflow-job outcomes into the generic
    objective-repair lifecycle.

    This service consumes already-persisted PlatformJob facts.
    It does not subscribe to platform events and does not launch,
    resume, or execute workflows.
    """

    SUPPORTED_JOB_TYPES = frozenset(
        {
            "workflow.run",
            "workflow.resume",
        }
    )

    def __init__(
        self,
        db: AsyncSession,
        *,
        jobs: JobRepository | None = None,
        repairs: (ObjectiveRepairExecutionRepository | None) = None,
        lifecycle: (ObjectiveRepairExecutionService | None) = None,
    ) -> None:
        self.db = db
        self.jobs = jobs or JobRepository(db)
        self.repairs = repairs or ObjectiveRepairExecutionRepository(db)
        self.lifecycle = lifecycle or ObjectiveRepairExecutionService(db)

    async def project_succeeded_job(
        self,
        *,
        user_id: UUID,
        workflow_job_id: UUID,
    ) -> CustomerSupportRepairLifecycleProjectionResult:
        job = await self._job_for_user(
            user_id=user_id,
            workflow_job_id=workflow_job_id,
        )

        repair_execution_id = self._repair_execution_id(job)

        if repair_execution_id is None:
            return self._ignored(
                workflow_job_id=workflow_job_id,
                reason="job_is_not_objective_repair",
            )

        repair = await self._repair_for_user(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        self._require_job_lineage(
            job=job,
            repair=repair,
        )

        if str(job.status) != "succeeded":
            raise CustomerSupportRepairLifecycleProjectionError(
                "Objective-repair workflow job is not succeeded"
            )

        result = self._dict(
            job.result,
            "workflow job result",
        )
        meta = self._dict(
            result.get("meta"),
            "workflow result meta",
        )

        workflow_status = self._required_text(
            meta.get("status"),
            "workflow result status",
        ).lower()

        workflow_run_id = self._required_text(
            (
                result.get("workflow_run_id")
                or result.get("run_id")
                or meta.get("workflow_run_id")
            ),
            "workflow_run_id",
        )

        if repair.status in (OBJECTIVE_REPAIR_EXECUTION_TERMINAL_STATUSES):
            return self._terminal_replay_result(
                repair=repair,
                workflow_job_id=workflow_job_id,
                workflow_run_id=workflow_run_id,
                result=result,
            )

        running = await self.lifecycle.mark_running(
            user_id=user_id,
            repair_execution_id=repair.id,
            workflow_run_id=workflow_run_id,
            commit=False,
        )

        if workflow_status == "paused":
            projected = await self.lifecycle.mark_paused(
                user_id=user_id,
                repair_execution_id=running.id,
                workflow_run_id=workflow_run_id,
                result_json=result,
                commit=False,
            )
            reason = "workflow_paused"

        elif workflow_status == "ok":
            repair_result = self._repair_result(result)

            if str(repair_result.get("status") or "").strip().lower() == "rejected":
                projected = await self.lifecycle.mark_rejected(
                    user_id=user_id,
                    repair_execution_id=running.id,
                    workflow_run_id=(workflow_run_id),
                    result_json=result,
                    commit=False,
                )
                reason = "workflow_rejected"
            else:
                projected = await self.lifecycle.mark_completed(
                    user_id=user_id,
                    repair_execution_id=running.id,
                    workflow_run_id=(workflow_run_id),
                    result_json=result,
                    commit=False,
                )
                reason = "workflow_completed"

        else:
            raise CustomerSupportRepairLifecycleProjectionError(
                "Succeeded workflow job contains unsupported "
                f"runtime status: {workflow_status}"
            )

        await self.db.commit()
        await self.db.refresh(projected)

        return CustomerSupportRepairLifecycleProjectionResult(
            repair_execution=projected,
            projected=True,
            reason=reason,
            workflow_job_id=workflow_job_id,
        )

    async def project_dead_lettered_job(
        self,
        *,
        user_id: UUID,
        workflow_job_id: UUID,
        error_message: str | None = None,
    ) -> CustomerSupportRepairLifecycleProjectionResult:
        job = await self._job_for_user(
            user_id=user_id,
            workflow_job_id=workflow_job_id,
        )

        repair_execution_id = self._repair_execution_id(job)

        if repair_execution_id is None:
            return self._ignored(
                workflow_job_id=workflow_job_id,
                reason="job_is_not_objective_repair",
            )

        repair = await self._repair_for_user(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        self._require_job_lineage(
            job=job,
            repair=repair,
        )

        if str(job.status) != "dead_letter":
            raise CustomerSupportRepairLifecycleProjectionError(
                "Objective-repair workflow job is not dead-lettered"
            )

        normalized_error = self._required_text(
            error_message or job.error_message,
            "workflow job error_message",
        )

        workflow_run_id = self._workflow_run_id_from_job(job) or repair.workflow_run_id

        if repair.status == OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED:
            if (
                repair.failure_code == "workflow_job_dead_lettered"
                and repair.failure_message == normalized_error
            ):
                return CustomerSupportRepairLifecycleProjectionResult(
                    repair_execution=repair,
                    projected=False,
                    reason="already_failed",
                    workflow_job_id=workflow_job_id,
                )

            raise ObjectiveRepairExecutionConflictError(
                "Objective repair was already failed with different job facts"
            )

        if repair.status in {
            OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED,
            OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED,
        }:
            raise CustomerSupportRepairLifecycleProjectionError(
                "Dead-lettered workflow job cannot replace a completed repair result"
            )

        failed = await self.lifecycle.mark_failed(
            user_id=user_id,
            repair_execution_id=repair.id,
            workflow_run_id=workflow_run_id,
            failure_code=("workflow_job_dead_lettered"),
            failure_message=normalized_error,
            result_json={
                "workflow_job_id": str(job.id),
                "job_type": job.job_type,
                "job_status": job.status,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "error_message": normalized_error,
            },
            commit=False,
        )

        await self.db.commit()
        await self.db.refresh(failed)

        return CustomerSupportRepairLifecycleProjectionResult(
            repair_execution=failed,
            projected=True,
            reason="workflow_job_dead_lettered",
            workflow_job_id=workflow_job_id,
        )

    async def project_retryable_failed_job(
        self,
        *,
        user_id: UUID,
        workflow_job_id: UUID,
    ) -> CustomerSupportRepairLifecycleProjectionResult:
        job = await self._job_for_user(
            user_id=user_id,
            workflow_job_id=workflow_job_id,
        )

        repair_execution_id = self._repair_execution_id(job)

        if repair_execution_id is None:
            return self._ignored(
                workflow_job_id=workflow_job_id,
                reason="job_is_not_objective_repair",
            )

        await self._repair_for_user(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        if str(job.status) != "queued":
            raise CustomerSupportRepairLifecycleProjectionError(
                "Retryable failed job must have returned to queued status"
            )

        return CustomerSupportRepairLifecycleProjectionResult(
            repair_execution=None,
            projected=False,
            reason="workflow_job_retry_scheduled",
            workflow_job_id=workflow_job_id,
        )

    async def _job_for_user(
        self,
        *,
        user_id: UUID,
        workflow_job_id: UUID,
    ) -> PlatformJob:
        job = await self.jobs.get(workflow_job_id)

        if job is None or job.user_id != user_id:
            raise CustomerSupportRepairLifecycleProjectionError(
                "Workflow job was not found for user"
            )

        if job.job_type not in self.SUPPORTED_JOB_TYPES:
            raise CustomerSupportRepairLifecycleProjectionError(
                "Job is not a supported workflow job"
            )

        return job

    async def _repair_for_user(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
    ) -> ObjectiveRepairExecutionRecord:
        repair = await self.repairs.get_by_id_for_user(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        if repair is None:
            raise ObjectiveRepairExecutionNotFoundError(
                "objective repair execution was not found"
            )

        return repair

    @staticmethod
    def _require_job_lineage(
        *,
        job: PlatformJob,
        repair: ObjectiveRepairExecutionRecord,
    ) -> None:
        if job.job_type == "workflow.run":
            if repair.workflow_job_id != job.id:
                raise CustomerSupportRepairLifecycleProjectionError(
                    "Workflow job does not match objective repair execution"
                )
            return

        workflow_run_id = (
            CustomerSupportRepairLifecycleProjector._workflow_run_id_from_job(job)
        )

        if repair.workflow_run_id is None or workflow_run_id != repair.workflow_run_id:
            raise CustomerSupportRepairLifecycleProjectionError(
                "Workflow resume job does not match the objective repair workflow run"
            )

    @staticmethod
    def _repair_execution_id(
        job: PlatformJob,
    ) -> UUID | None:
        payload = job.payload if isinstance(job.payload, dict) else {}
        extras = payload.get("extras")

        if not isinstance(extras, dict):
            return None

        repair_context = extras.get("objective_repair")

        if not isinstance(repair_context, dict):
            return None

        raw_id = repair_context.get("repair_execution_id")

        if raw_id is None:
            return None

        try:
            return UUID(str(raw_id))
        except ValueError as exc:
            raise CustomerSupportRepairLifecycleProjectionError(
                "Objective-repair workflow job contains invalid repair_execution_id"
            ) from exc

    @staticmethod
    def _workflow_run_id_from_job(
        job: PlatformJob,
    ) -> str | None:
        result = job.result if isinstance(job.result, dict) else {}
        meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
        payload = job.payload if isinstance(job.payload, dict) else {}

        raw = (
            result.get("workflow_run_id")
            or result.get("run_id")
            or meta.get("workflow_run_id")
            or payload.get("workflow_run_id")
            or payload.get("run_id")
        )

        normalized = str(raw or "").strip()
        return normalized or None

    @staticmethod
    def _repair_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        meta = result.get("meta")

        if not isinstance(meta, dict):
            return {}

        final_state = meta.get("final_state")

        if not isinstance(final_state, dict):
            return {}

        variables = final_state.get("vars")

        if not isinstance(variables, dict):
            return {}

        candidate = variables.get("repair_result")

        if isinstance(candidate, dict):
            return candidate

        candidate = variables.get("repair_control_result")

        if isinstance(candidate, dict):
            return candidate

        return {}

    @staticmethod
    def _dict(
        value: Any,
        field_name: str,
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise CustomerSupportRepairLifecycleProjectionError(
                f"{field_name} must be an object"
            )

        return value

    @staticmethod
    def _required_text(
        value: Any,
        field_name: str,
    ) -> str:
        normalized = str(value or "").strip()

        if not normalized:
            raise CustomerSupportRepairLifecycleProjectionError(
                f"{field_name} is required"
            )

        return normalized

    @staticmethod
    def _ignored(
        *,
        workflow_job_id: UUID,
        reason: str,
    ) -> CustomerSupportRepairLifecycleProjectionResult:
        return CustomerSupportRepairLifecycleProjectionResult(
            repair_execution=None,
            projected=False,
            reason=reason,
            workflow_job_id=workflow_job_id,
        )

    @staticmethod
    def _terminal_replay_result(
        *,
        repair: ObjectiveRepairExecutionRecord,
        workflow_job_id: UUID,
        workflow_run_id: str,
        result: dict[str, Any],
    ) -> CustomerSupportRepairLifecycleProjectionResult:
        if repair.workflow_run_id != workflow_run_id:
            raise ObjectiveRepairExecutionConflictError(
                "Terminal objective repair belongs to a different workflow run"
            )

        if repair.result_json != result:
            raise ObjectiveRepairExecutionConflictError(
                "Terminal objective repair was recorded "
                "with different workflow result facts"
            )

        return CustomerSupportRepairLifecycleProjectionResult(
            repair_execution=repair,
            projected=False,
            reason="already_terminal",
            workflow_job_id=workflow_job_id,
        )


__all__ = [
    "CustomerSupportRepairLifecycleProjectionError",
    "CustomerSupportRepairLifecycleProjectionResult",
    "CustomerSupportRepairLifecycleProjector",
]
