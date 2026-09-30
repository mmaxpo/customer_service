from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.support.repair.review_plan import (
    CustomerSupportRepairReviewPlanBuilder,
)
from app.domains.customer_service.services.support.repair.workflow import (
    CustomerSupportRepairWorkflowBuilder,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan_loader import (
    CustomerSupportReviewPlanLoader,
)
from app.models.models import (
    ObjectiveRepairExecutionRecord,
    PlatformJob,
)
from app.platform.jobs.repository import JobRepository
from app.platform.jobs.service import JobService
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED,
    ObjectiveRepairDisposition,
    ObjectiveRepairExecutionNotFoundError,
    ObjectiveRepairExecutionRepository,
    ObjectiveRepairExecutionService,
    ObjectiveRepairExecutionTransitionError,
    ObjectiveRepairPlan,
)
from app.runtime.validation import (
    validate_workflow,
)


class CustomerSupportRepairLaunchError(RuntimeError):
    pass


@dataclass(frozen=True)
class CustomerSupportRepairLaunchResult:
    repair_execution: ObjectiveRepairExecutionRecord
    workflow_job: PlatformJob
    workflow: dict
    already_queued: bool


class CustomerSupportRepairLaunchCoordinator:
    """
    Build and durably enqueue one customer-support repair workflow.

    Responsibilities:
    - load the generic durable repair execution with user scoping;
    - deserialize and verify the persisted repair plan;
    - select the correct customer-support workflow builder;
    - load the canonical source review plan only when provider
      operations must be replanned;
    - validate the generated workflow;
    - atomically create/reuse the workflow.run job and move the
      repair execution from planned to queued.

    Runtime completion and pause projection are owned by later
    lifecycle wiring.
    """

    WORKFLOW_JOB_TYPE = "workflow.run"

    def __init__(
        self,
        db: AsyncSession,
        *,
        repairs: (ObjectiveRepairExecutionRepository | None) = None,
        lifecycle: (ObjectiveRepairExecutionService | None) = None,
        review_plan_loader: (CustomerSupportReviewPlanLoader | None) = None,
        repair_review_builder: (CustomerSupportRepairReviewPlanBuilder | None) = None,
        workflow_builder: (CustomerSupportRepairWorkflowBuilder | None) = None,
        jobs: JobService | None = None,
        job_repository: JobRepository | None = None,
    ) -> None:
        self.db = db
        self.repairs = repairs or ObjectiveRepairExecutionRepository(db)
        self.lifecycle = lifecycle or ObjectiveRepairExecutionService(db)
        self.review_plan_loader = review_plan_loader or CustomerSupportReviewPlanLoader(
            db
        )
        self.repair_review_builder = (
            repair_review_builder or CustomerSupportRepairReviewPlanBuilder()
        )
        self.workflow_builder = (
            workflow_builder or CustomerSupportRepairWorkflowBuilder()
        )
        self.jobs = jobs or JobService(db)
        self.job_repository = job_repository or JobRepository(db)

    async def launch(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
    ) -> CustomerSupportRepairLaunchResult:
        record = await self.repairs.get_by_id_for_user(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        if record is None:
            raise ObjectiveRepairExecutionNotFoundError(
                "objective repair execution was not found"
            )

        if record.status == OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED:
            return await self._existing_launch(
                record=record,
            )

        if record.status != OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED:
            raise ObjectiveRepairExecutionTransitionError(
                "objective repair workflow can only be launched from planned status"
            )

        repair_plan = self._repair_plan(record)

        self._require_record_plan_consistency(
            record=record,
            repair_plan=repair_plan,
        )

        workflow = await self._build_workflow(
            record=record,
            repair_plan=repair_plan,
        )

        self._validate_workflow(workflow)

        execution_id = str(record.id)

        workflow_job = await self.jobs.enqueue(
            user_id=user_id,
            job_type=self.WORKFLOW_JOB_TYPE,
            payload={
                "workflow": workflow,
                "message": (f"Customer-support objective repair ready: {execution_id}"),
                "extras": {
                    "customer_service": True,
                    "objective_repair": (
                        self.workflow_builder.objective_repair_extras(
                            repair_execution_id=execution_id,
                            resolution_record_id=str(record.resolution_record_id),
                            attempt_number=(record.attempt_number),
                            repair_plan=repair_plan,
                        )
                    ),
                },
            },
            max_attempts=5,
            idempotency_key=(
                self.workflow_builder.workflow_job_idempotency_key(
                    repair_execution_id=execution_id,
                )
            ),
            commit=False,
        )

        queued = await self.lifecycle.queue_workflow(
            user_id=user_id,
            repair_execution_id=record.id,
            workflow_json=workflow,
            workflow_job_id=workflow_job.id,
            commit=False,
        )

        await self.db.commit()
        await self.db.refresh(queued)
        await self.db.refresh(workflow_job)

        return CustomerSupportRepairLaunchResult(
            repair_execution=queued,
            workflow_job=workflow_job,
            workflow=workflow,
            already_queued=False,
        )

    async def _existing_launch(
        self,
        *,
        record: ObjectiveRepairExecutionRecord,
    ) -> CustomerSupportRepairLaunchResult:
        if (
            record.workflow_job_id is None
            or not isinstance(record.workflow_json, dict)
            or not record.workflow_json
        ):
            raise CustomerSupportRepairLaunchError(
                "Queued objective repair execution has incomplete workflow linkage"
            )

        workflow_job = await self.job_repository.get(record.workflow_job_id)

        if workflow_job is None:
            raise CustomerSupportRepairLaunchError(
                "Queued objective repair workflow job was not found"
            )

        if workflow_job.user_id != record.user_id:
            raise CustomerSupportRepairLaunchError(
                "Objective repair workflow job ownership "
                "does not match repair execution"
            )

        if workflow_job.job_type != self.WORKFLOW_JOB_TYPE:
            raise CustomerSupportRepairLaunchError(
                "Objective repair workflow job has unexpected job type"
            )

        return CustomerSupportRepairLaunchResult(
            repair_execution=record,
            workflow_job=workflow_job,
            workflow=record.workflow_json,
            already_queued=True,
        )

    async def _build_workflow(
        self,
        *,
        record: ObjectiveRepairExecutionRecord,
        repair_plan: ObjectiveRepairPlan,
    ) -> dict:
        disposition = repair_plan.disposition

        common = {
            "repair_execution_id": str(record.id),
            "resolution_record_id": str(record.resolution_record_id),
            "attempt_number": record.attempt_number,
            "repair_plan": repair_plan,
        }

        if disposition == ObjectiveRepairDisposition.REPLAN_REMAINING:
            loaded = await self.review_plan_loader.load_for_resolution(
                user_id=record.user_id,
                resolution_record_id=(record.resolution_record_id),
            )

            repair_review_plan = self.repair_review_builder.build(
                source_review_plan=(loaded.review_plan),
                repair_plan=repair_plan,
            )

            return self.workflow_builder.build_replanned_operations(
                **common,
                repair_review_plan=(repair_review_plan),
            )

        if disposition in {
            ObjectiveRepairDisposition.WAIT_FOR_RESULT,
            ObjectiveRepairDisposition.REQUEST_HUMAN_ACTION,
            ObjectiveRepairDisposition.STOP_REPAIR,
        }:
            return self.workflow_builder.build_non_mutating(
                **common,
            )

        raise CustomerSupportRepairLaunchError(
            "Unsupported customer-support repair "
            f"launch disposition: {disposition.value}"
        )

    @staticmethod
    def _repair_plan(
        record: ObjectiveRepairExecutionRecord,
    ) -> ObjectiveRepairPlan:
        try:
            return ObjectiveRepairPlan.model_validate(record.plan_json)
        except Exception as exc:
            raise CustomerSupportRepairLaunchError(
                "Persisted objective repair plan is invalid"
            ) from exc

    @staticmethod
    def _require_record_plan_consistency(
        *,
        record: ObjectiveRepairExecutionRecord,
        repair_plan: ObjectiveRepairPlan,
    ) -> None:
        if repair_plan.disposition.value != record.controlling_disposition:
            raise CustomerSupportRepairLaunchError(
                "Persisted objective repair disposition "
                "does not match execution metadata"
            )

        if (
            repair_plan.objective.namespace != record.objective_namespace
            or repair_plan.objective.objective_type != record.objective_type
            or repair_plan.objective.objective_ref != record.objective_ref
            or repair_plan.objective.objective_version != record.objective_version
        ):
            raise CustomerSupportRepairLaunchError(
                "Persisted objective repair objective does not match execution metadata"
            )

        if repair_plan.repair_request_ref != record.repair_request_ref:
            raise CustomerSupportRepairLaunchError(
                "Persisted objective repair request does not match execution metadata"
            )

        if repair_plan.automatic_execution_allowed:
            raise CustomerSupportRepairLaunchError(
                "Customer-support repair workflow cannot allow automatic execution"
            )

    @staticmethod
    def _validate_workflow(
        workflow: dict,
    ) -> None:
        errors = validate_workflow(
            workflow,
            strict=True,
        )

        if not errors:
            return

        details = "; ".join(
            (
                f"{item.code}: {item.message}"
                if getattr(item, "code", None)
                else str(item)
            )
            for item in errors
        )

        raise CustomerSupportRepairLaunchError(
            f"Generated customer-support repair workflow is invalid: {details}"
        )


__all__ = [
    "CustomerSupportRepairLaunchCoordinator",
    "CustomerSupportRepairLaunchError",
    "CustomerSupportRepairLaunchResult",
]
