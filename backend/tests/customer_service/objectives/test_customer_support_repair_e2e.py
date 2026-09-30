from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB,
)
from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.models.models import (
    ObjectiveRepairExecutionRecord,
    ObjectiveResolutionRecord,
    PlatformJob,
)
from app.node_registration import register_application_nodes
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.platform.jobs.worker import JobWorker
from app.runtime.engine.persistence.postgres import (
    PostgresRunStore,
)
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED,
    OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED,
    ObjectiveRepairAction,
    ObjectiveRepairConstraints,
    ObjectiveRepairDisposition,
    ObjectiveRepairExecutionService,
    ObjectiveRepairPlan,
    ObjectiveRepairRequest,
    ObjectiveRepairSource,
    ObjectiveRepairTarget,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionStatus,
)
from app.workflow_operations.waits.service import (
    WorkflowWaitService,
)


def _source_review_plan() -> SupportReviewPlan:
    return SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        provider_order_id=("gid://shopify/Order/1001"),
        operations=[
            SupportReviewOperation(
                operation_ref=("support_operation:001:partial_refund:line-1"),
                operation_type=(SupportReviewOperationType.PARTIAL_REFUND),
                item_id="line-1",
                item_label="Snowboard",
                approval_required=True,
                execution_allowed=False,
            ),
        ],
        approval_required=True,
        execution_allowed=False,
        source_objective_version=3,
    )


def _source_workflow(
    *,
    review_plan_id: str,
    plan: SupportReviewPlan,
) -> dict:
    support_review = {
        "review_plan_id": review_plan_id,
        "review_plan": plan.model_dump(mode="json"),
    }

    return {
        "name": (f"Original Customer Support Review {review_plan_id}"),
        "version": "1.0.0",
        "nodes": [],
        "edges": [],
        "metadata": {
            "kind": "customer_support_review",
            "review_plan_id": review_plan_id,
            "approval_required": True,
            "provider": plan.provider,
            "order_ref": plan.order_ref,
            "support_review": support_review,
        },
    }


async def _persist_source_lineage(
    db,
    *,
    user_id,
) -> dict:
    review_plan_id = str(uuid4())
    support_outcome_id = uuid4()
    resolution_record_id = uuid4()
    source_workflow_run_id = uuid4()
    source_plan = _source_review_plan()

    await PostgresRunStore(db).create_run(
        run_id=source_workflow_run_id,
        user_id=user_id,
        thread_id=None,
        workflow=_source_workflow(
            review_plan_id=review_plan_id,
            plan=source_plan,
        ),
        state={
            "workflow_run_id": str(source_workflow_run_id),
            "vars": {},
        },
        status="completed",
        extra={},
    )

    outcome = CustomerSupportOutcomeRecord(
        id=support_outcome_id,
        user_id=user_id,
        review_plan_id=review_plan_id,
        workflow_run_id=source_workflow_run_id,
        chat_session_id=uuid4(),
        conversation_id=uuid4(),
        objective_namespace=("customer_service.support"),
        objective_ref=review_plan_id,
        source_objective_version=(source_plan.source_objective_version),
        outcome_version=1,
        objective_type="multi_operation",
        order_ref=source_plan.order_ref,
        decision="approved",
        status="failed",
        operation_count=1,
        customer_message=("The reviewed refund operation failed."),
        operations_json=[],
        outcome_json={
            "version": 1,
            "review_plan_id": review_plan_id,
            "order_ref": source_plan.order_ref,
            "decision": "approved",
            "operations": [],
            "customer_message": ("The reviewed refund operation failed."),
        },
    )
    db.add(outcome)

    source_event = await PlatformEventStore(db).append(
        event_type=("customer_service.support.outcome.evaluated"),
        source=("customer_service.support_outcome_evaluation"),
        user_id=user_id,
        payload={
            "support_outcome_id": str(support_outcome_id),
            "review_plan_id": review_plan_id,
        },
        meta={
            "workflow_run_id": str(source_workflow_run_id),
        },
        commit=False,
    )

    resolution = ObjectiveResolutionRecord(
        id=resolution_record_id,
        source_event_id=source_event.id,
        user_id=user_id,
        tenant_id="tenant-1",
        objective_namespace=("customer_service.support"),
        objective_type="multi_operation",
        objective_ref=review_plan_id,
        objective_version=(source_plan.source_objective_version),
        source_outcome_ref=str(support_outcome_id),
        outcome_version=1,
        source_evaluation_ref=str(uuid4()),
        evaluation_version=1,
        projection_version=1,
        assessment_schema_version=("objective_resolution_assessment.v1"),
        workflow_run_id=str(source_workflow_run_id),
        status="failed",
        reason_code=("one_or_more_operations_failed"),
        summary=("The required refund operation failed."),
        confidence=0.95,
        is_terminal=False,
        operation_count=1,
        achieved_operation_count=0,
        unresolved_operation_count=1,
        failed_operation_count=1,
        pending_operation_count=0,
        unknown_operation_count=0,
        not_executed_operation_count=0,
        assessment_json={
            "schema_version": ("objective_resolution_assessment.v1"),
            "objective": {
                "namespace": ("customer_service.support"),
                "objective_type": ("multi_operation"),
                "objective_ref": review_plan_id,
                "objective_version": (source_plan.source_objective_version),
            },
        },
    )
    db.add(resolution)

    await db.commit()

    return {
        "review_plan_id": review_plan_id,
        "support_outcome_id": (support_outcome_id),
        "resolution_record_id": (resolution_record_id),
        "source_workflow_run_id": (source_workflow_run_id),
        "source_plan": source_plan,
    }


def _repair_request(
    *,
    lineage: dict,
) -> ObjectiveRepairRequest:
    operation_ref = lineage["source_plan"].operations[0].operation_ref

    objective = ObjectiveReference(
        namespace="customer_service.support",
        objective_type="multi_operation",
        objective_ref=lineage["review_plan_id"],
        objective_version=(lineage["source_plan"].source_objective_version),
    )

    return ObjectiveRepairRequest(
        repair_request_ref=(f"objective-repair:{lineage['resolution_record_id']}:v1"),
        source=ObjectiveRepairSource(
            resolution_record_ref=str(lineage["resolution_record_id"]),
            objective=objective,
            outcome_ref=str(lineage["support_outcome_id"]),
            outcome_version=1,
            evaluation_ref=str(uuid4()),
            evaluation_version=1,
            resolution_projection_version=1,
            workflow_run_id=str(lineage["source_workflow_run_id"]),
        ),
        resolution_status=(ObjectiveResolutionStatus.FAILED),
        resolution_reason_code=("one_or_more_operations_failed"),
        resolution_summary=("The required refund operation failed."),
        resolution_confidence=0.95,
        targets=(
            ObjectiveRepairTarget(
                operation_ref=operation_ref,
                operation_type="partial_refund",
                resolution_status=(ObjectiveOperationStatus.FAILED),
                required=True,
                reason_code="provider_failure",
                summary="Refund operation failed.",
                source_task_id="task-refund",
                verification_ref=("verification-refund"),
                evidence_refs=("evidence-refund",),
            ),
        ),
        constraints=ObjectiveRepairConstraints(
            allow_automatic_execution=False,
            require_human_approval=True,
            allowed_dispositions=(ObjectiveRepairDisposition.REPLAN_REMAINING,),
        ),
    )


def _repair_plan(
    *,
    request: ObjectiveRepairRequest,
) -> ObjectiveRepairPlan:
    operation_ref = request.targets[0].operation_ref

    return ObjectiveRepairPlan(
        repair_request_ref=(request.repair_request_ref),
        objective=request.source.objective,
        disposition=(ObjectiveRepairDisposition.REPLAN_REMAINING),
        reason_code=("support_repair_requires_replanning"),
        summary=("Rebuild the failed refund operation behind a new approval."),
        confidence=0.95,
        actions=(
            ObjectiveRepairAction(
                action_ref=(
                    f"support-repair:request:001:replan_remaining:{operation_ref}"
                ),
                disposition=(ObjectiveRepairDisposition.REPLAN_REMAINING),
                target_operation_refs=(operation_ref,),
                reason_code=("support_operation_failed_requires_replan"),
                summary=("Rebuild the failed refund operation."),
                confidence=0.95,
                automatic_execution_allowed=False,
                human_approval_required=True,
                planner_directives={
                    "require_new_human_approval": (True),
                },
            ),
        ),
        planned_target_refs=(operation_ref,),
        deferred_target_refs=(),
        unhandled_target_refs=(),
        automatic_execution_allowed=False,
        human_approval_required=True,
        planner_metadata={
            "planner": ("customer_support_objective_repair.v1"),
            "policy_version": 1,
        },
    )


async def _jobs_for_user(
    db,
    *,
    user_id,
    job_type: str,
) -> list[PlatformJob]:
    result = await db.execute(
        select(PlatformJob)
        .where(
            PlatformJob.user_id == user_id,
            PlatformJob.job_type == job_type,
        )
        .order_by(PlatformJob.created_at.asc())
    )

    return list(result.scalars().all())


async def _repair_for_user(
    db,
    *,
    user_id,
    repair_execution_id,
) -> ObjectiveRepairExecutionRecord:
    result = await db.execute(
        select(ObjectiveRepairExecutionRecord).where(
            ObjectiveRepairExecutionRecord.user_id == user_id,
            ObjectiveRepairExecutionRecord.id == repair_execution_id,
        )
    )

    repair = result.scalar_one_or_none()
    assert repair is not None
    return repair


@pytest.mark.asyncio
async def test_repair_plan_launch_pause_reject_resume_projects_terminally():
    register_application_nodes()

    user_id = uuid4()

    # ---------------------------------------------------------
    # 1. Persist canonical source lineage and a repair plan.
    #    record_plan dispatches the real planned-event handler,
    #    which creates the real launch job.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        lineage = await _persist_source_lineage(
            db,
            user_id=user_id,
        )

        request = _repair_request(lineage=lineage)
        plan = _repair_plan(request=request)

        repair_source_event = await PlatformEventStore(db).append(
            event_type=("runtime.objective.resolution.repair_requested"),
            source=("runtime.objective_resolution"),
            user_id=user_id,
            payload={
                "resolution_record_id": str(lineage["resolution_record_id"]),
            },
            meta={},
        )

        write = await ObjectiveRepairExecutionService(db).record_plan(
            source_event_id=(repair_source_event.id),
            user_id=user_id,
            tenant_id="tenant-1",
            resolution_record_id=(lineage["resolution_record_id"]),
            request=request,
            plan=plan,
            planner_ref=("customer_support_objective_repair"),
            planner_policy_version=1,
            attempt_number=1,
        )

        repair_execution_id = write.record.id

        assert write.created is True
        assert write.event_id is not None
        assert write.record.status == "planned"

        launch_jobs = await _jobs_for_user(
            db,
            user_id=user_id,
            job_type=(CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB),
        )

        assert len(launch_jobs) == 1
        launch_job_id = launch_jobs[0].id
        assert launch_jobs[0].status == "queued"
        assert launch_jobs[0].payload["repair_execution_id"] == str(repair_execution_id)

    # ---------------------------------------------------------
    # 2. Run the real launch job. It loads the canonical source
    #    review plan, builds the repair workflow, creates one
    #    workflow.run job, and changes repair to queued.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        launch_job = await JobWorker(
            db,
            worker_id=(f"repair-e2e-launch-{uuid4()}"),
        ).run_once(job_id=launch_job_id)

        assert launch_job is not None
        assert launch_job.status == "succeeded"

        repair = await _repair_for_user(
            db,
            user_id=user_id,
            repair_execution_id=(repair_execution_id),
        )

        assert repair.status == "queued"
        assert repair.workflow_job_id is not None
        assert repair.workflow_json is not None

        workflow_job_id = repair.workflow_job_id

        workflow_job = await db.get(
            PlatformJob,
            workflow_job_id,
        )

        assert workflow_job is not None
        assert workflow_job.job_type == ("workflow.run")
        assert workflow_job.status == "queued"
        assert workflow_job.payload["extras"]["objective_repair"][
            "repair_execution_id"
        ] == str(repair_execution_id)

    # ---------------------------------------------------------
    # 3. Run the repair workflow to its real human-approval
    #    boundary. The job.succeeded event projects the repair
    #    from queued -> running -> paused.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        started_job = await JobWorker(
            db,
            worker_id=(f"repair-e2e-start-{uuid4()}"),
        ).run_once(job_id=workflow_job_id)

        assert started_job is not None
        assert started_job.status == "succeeded"
        assert started_job.result["meta"]["status"] == "paused"

        workflow_run_id = started_job.result["meta"]["workflow_run_id"]

        repair = await _repair_for_user(
            db,
            user_id=user_id,
            repair_execution_id=(repair_execution_id),
        )

        assert repair.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED)
        assert repair.workflow_run_id == (workflow_run_id)
        assert repair.result_json == (started_job.result)

        waits = await WorkflowWaitService(db).list_for_user(
            user_id=user_id,
            status="waiting",
            workflow_run_id=workflow_run_id,
        )

        approval_waits = [
            wait
            for wait in waits
            if (wait.wait_type == "approval" and wait.node_id == "repair_approval")
        ]

        assert len(approval_waits) == 1
        approval_wait_id = approval_waits[0].id

    # ---------------------------------------------------------
    # 4. Reject the durable approval. This must create one real
    #    workflow.resume job carrying the same repair identity.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        rejection = await WorkflowWaitService(db).reject(
            user_id=user_id,
            wait_id=approval_wait_id,
        )

        resume_job = rejection.get("resume_job")

        assert resume_job is not None
        assert resume_job.job_type == ("workflow.resume")
        assert resume_job.payload["workflow_run_id"] == workflow_run_id
        assert resume_job.payload["extras"]["objective_repair"][
            "repair_execution_id"
        ] == str(repair_execution_id)
        assert resume_job.payload["input"]["approved"] is False

        resume_job_id = resume_job.id

    # ---------------------------------------------------------
    # 5. Run the real resume job. Its job.succeeded event must
    #    project the same repair execution to rejected.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        resumed_job = await JobWorker(
            db,
            worker_id=(f"repair-e2e-resume-{uuid4()}"),
        ).run_once(job_id=resume_job_id)

        assert resumed_job is not None
        assert resumed_job.status == "succeeded"
        assert resumed_job.result["meta"]["status"] == "ok"
        assert resumed_job.result["meta"]["workflow_run_id"] == (workflow_run_id)

        repair_result = resumed_job.result["meta"]["final_state"]["vars"][
            "repair_result"
        ]

        assert repair_result["status"] == ("rejected")

        repair = await _repair_for_user(
            db,
            user_id=user_id,
            repair_execution_id=(repair_execution_id),
        )

        assert repair.status == (OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED)
        assert repair.workflow_run_id == (workflow_run_id)
        assert repair.result_json == (resumed_job.result)
        assert repair.failure_code is None
        assert repair.failure_message is None
        assert repair.completed_at is not None

        saved_wait = await WorkflowWaitService(db).get_for_user(
            user_id=user_id,
            wait_id=approval_wait_id,
        )

        assert saved_wait.status == "resolved"
        assert saved_wait.resolution == {
            "approved": False,
            "action": "rejected",
        }

        resume_jobs = await _jobs_for_user(
            db,
            user_id=user_id,
            job_type="workflow.resume",
        )

        assert len(resume_jobs) == 1
        assert resume_jobs[0].id == (resume_job_id)
