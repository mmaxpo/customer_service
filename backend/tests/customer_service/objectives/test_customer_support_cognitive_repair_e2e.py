from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

# Initialize the canonical aggregate model graph before loading
# the existing customer-service E2E helper module.
import app.models.models  # noqa: F401
from app.core.session import SessionLocal
from app.domains.customer_service.jobs.handlers import (
    CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB,
)
from app.domains.customer_service.services.support.repair.planning import (
    CustomerSupportRepairPlanningCoordinator,
)
from app.models.models import (
    ObjectiveRepairExecutionRecord,
    ObjectiveResolutionRecord,
    PlatformJob,
)
from app.platform.jobs.worker import JobWorker
from app.runtime.objectives.cognition import (
    ObjectiveCognitiveReference,
)
from app.runtime.objectives.repair import (
    ObjectiveRepairExecutionConflictError,
)
from app.runtime.objectives.resolution import (
    ObjectiveOperationResolution,
    ObjectiveOperationStatus,
    ObjectiveReference,
    ObjectiveResolutionAssessment,
    ObjectiveResolutionSource,
    ObjectiveResolutionStatus,
)
from app.tcos.cognitive import (
    OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY,
    OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY,
    CognitiveRuntime,
    ObjectiveRepairDelegationDecision,
    ObjectiveRepairDelegationKind,
)


def _load_existing_repair_e2e_helpers():
    """
    Load the established durable lineage and query helpers.

    The helpers remain owned by the existing repair E2E test. This
    test reuses them rather than introducing duplicate production or
    shared-fixture code solely for Slice 6D.
    """

    path = Path("tests/customer_service/objectives/test_customer_support_repair_e2e.py")

    spec = importlib.util.spec_from_file_location(
        "slice_6d_existing_repair_e2e_helpers",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load existing repair E2E helpers")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    required = (
        "_persist_source_lineage",
        "_jobs_for_user",
        "_repair_for_user",
    )

    missing = [name for name in required if getattr(module, name, None) is None]

    if missing:
        raise RuntimeError(
            "Existing repair E2E helpers are missing: " + ", ".join(missing)
        )

    return SimpleNamespace(
        persist_source_lineage=(module._persist_source_lineage),
        jobs_for_user=module._jobs_for_user,
        repair_for_user=module._repair_for_user,
    )


HELPERS = _load_existing_repair_e2e_helpers()


async def _persist_complete_resolution_assessment(
    db,
    *,
    lineage: dict,
) -> ObjectiveResolutionAssessment:
    """
    Upgrade the reused historical E2E fixture to the complete
    durable assessment contract consumed by product planning.

    The existing helper predates typed reconstruction and stores
    only objective identity in assessment_json. Slice 6D requires
    the full business-truth projection because the product repair
    coordinator reconstructs ObjectiveResolutionAssessment from
    the durable record.
    """

    resolution = await db.get(
        ObjectiveResolutionRecord,
        lineage["resolution_record_id"],
    )

    if resolution is None:
        raise AssertionError("Persisted objective resolution was not found")

    source_plan = lineage["source_plan"]

    if len(source_plan.operations) != 1:
        raise AssertionError("Slice 6D fixture requires exactly one source operation")

    source_operation = source_plan.operations[0]

    operation_type = source_operation.operation_type

    if hasattr(operation_type, "value"):
        operation_type = operation_type.value

    assessment = ObjectiveResolutionAssessment(
        schema_version=(resolution.assessment_schema_version),
        objective=ObjectiveReference(
            namespace=resolution.objective_namespace,
            objective_type=resolution.objective_type,
            objective_ref=resolution.objective_ref,
            objective_version=(resolution.objective_version),
        ),
        source=ObjectiveResolutionSource(
            outcome_ref=resolution.source_outcome_ref,
            outcome_version=resolution.outcome_version,
            evaluation_ref=(resolution.source_evaluation_ref),
            evaluation_version=(resolution.evaluation_version),
            workflow_run_id=resolution.workflow_run_id,
        ),
        status=ObjectiveResolutionStatus(resolution.status),
        reason_code=resolution.reason_code,
        summary=resolution.summary,
        confidence=resolution.confidence,
        is_terminal=resolution.is_terminal,
        operations=(
            ObjectiveOperationResolution(
                operation_ref=(source_operation.operation_ref),
                operation_type=str(operation_type),
                status=ObjectiveOperationStatus.FAILED,
                required=True,
                reason_code=("support_operation_execution_failed"),
                summary=("The required support operation failed."),
                metadata={
                    "review_plan_id": (lineage["review_plan_id"]),
                },
            ),
        ),
        evidence_refs=(str(resolution.source_event_id),),
        metadata={
            "tenant_id": resolution.tenant_id,
            "projection_version": (resolution.projection_version),
        },
    )

    resolution.assessment_json = assessment.model_dump(mode="json")

    await db.commit()
    await db.refresh(resolution)

    reconstructed = ObjectiveResolutionAssessment.model_validate(
        resolution.assessment_json
    )

    assert reconstructed == assessment
    assert reconstructed.failed_operation_refs == (source_operation.operation_ref,)
    assert reconstructed.unresolved_operation_refs == (source_operation.operation_ref,)

    return reconstructed


@pytest.mark.asyncio
async def test_durable_cognition_delegates_product_repair_and_launches_once():
    """
    Verify the complete Slice 6 objective-to-repair boundary.

    Generic cognition:
      - loads durable objective truth,
      - transports it into planning,
      - reasons about repair delegation independently of whether
        ordinary goal planning produces a candidate,
      - projects informational lifecycle telemetry.

    Product orchestration then explicitly accepts the typed
    delegation and owns:
      - canonical source loading,
      - product repair planning,
      - durable repair persistence,
      - planned-event publication,
      - launch-job scheduling,
      - repair workflow construction and queueing.

    Replaying the same typed delegation must converge on the same
    repair execution and must not schedule another launch.
    """

    user_id = uuid4()
    tenant_id = "tenant-1"

    # ---------------------------------------------------------
    # 1. Persist the canonical durable customer-support lineage.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        lineage = await HELPERS.persist_source_lineage(
            db,
            user_id=user_id,
        )

        durable_assessment = await _persist_complete_resolution_assessment(
            db,
            lineage=lineage,
        )

        assert durable_assessment.status == (ObjectiveResolutionStatus.FAILED)
        assert durable_assessment.is_terminal is False
        assert len(durable_assessment.operations) == 1
        assert (
            durable_assessment.operations[0].status == ObjectiveOperationStatus.FAILED
        )

        objective = ObjectiveCognitiveReference(
            namespace="customer_service.support",
            objective_ref=lineage["review_plan_id"],
        )

        # -----------------------------------------------------
        # 2. Run the real asynchronous cognitive entrypoint.
        #    Cognition may observe and delegate but cannot
        #    persist or launch product repair work itself.
        # -----------------------------------------------------

        cognitive_session = await CognitiveRuntime().execute_goal_runtime(
            goal=(
                "Review the failed refund objective and "
                "determine the appropriate next action."
            ),
            ctx=SimpleNamespace(
                db=db,
                user_id=user_id,
                tenant_id=tenant_id,
            ),
            objective=objective,
        )

        delegation_payload = cognitive_session.metrics[
            OBJECTIVE_REPAIR_DELEGATION_METRIC_KEY
        ]

        delegation = ObjectiveRepairDelegationDecision.model_validate(
            delegation_payload
        )

        assert delegation.kind == (
            ObjectiveRepairDelegationKind.REPAIR_PLANNING_REQUESTED
        )
        assert delegation.requested is True
        assert delegation.resolution_record_id == (lineage["resolution_record_id"])
        assert delegation.repair_execution_id is None
        assert delegation.current_attempt_number is None
        assert delegation.requested_attempt_number == 1

        assert delegation.safety.product_planning_required is True
        assert delegation.safety.persists_repair is False
        assert delegation.safety.publishes_event is False
        assert delegation.safety.enqueues_job is False
        assert delegation.safety.launches_workflow is False
        assert delegation.safety.authorizes_execution is False
        assert delegation.safety.bypasses_approval is False
        assert delegation.safety.bypasses_verification is False

        lifecycle = cognitive_session.metrics[OBJECTIVE_LIFECYCLE_TELEMETRY_METRIC_KEY]

        assert lifecycle["context_available"] is True
        assert lifecycle["objective_present"] is True
        assert lifecycle["resolution_available"] is True
        assert lifecycle["repair_available"] is False

        # Repair delegation is derived from durable objective truth.
        # This repair-review request is intentionally not an ordinary
        # goal-planning candidate.
        assert lifecycle["selected_candidate_observed"] is False
        assert lifecycle["repair_planning_requested"] is True
        assert lifecycle["requested_attempt_number"] == 1
        assert lifecycle["resolution_record_id"] == str(lineage["resolution_record_id"])
        assert lifecycle["repair_execution_id"] is None

        assert lifecycle["informational_only"] is True
        assert lifecycle["affects_score"] is False
        assert lifecycle["affects_ordering"] is False
        assert lifecycle["affects_capability_selection"] is False
        assert lifecycle["affects_business_plan"] is False
        assert lifecycle["persists_repair"] is False
        assert lifecycle["publishes_platform_event"] is False
        assert lifecycle["enqueues_job"] is False
        assert lifecycle["launches_repair"] is False
        assert lifecycle["authorizes_execution"] is False

        planner_session = cognitive_session.planner_session

        assert isinstance(planner_session, dict)
        assert planner_session["selected_candidate"] is None

        # Generic cognition must not have created repair state.
        repair_before_product_handoff = await HELPERS.jobs_for_user(
            db,
            user_id=user_id,
            job_type=(CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB),
        )

        assert repair_before_product_handoff == []

        # -----------------------------------------------------
        # 3. Perform the explicit product-layer handoff.
        #    The coordinator plans and persists; its real
        #    planned event schedules the existing launch job.
        # -----------------------------------------------------

        planning = await CustomerSupportRepairPlanningCoordinator(db).plan(
            decision=delegation,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        repair_execution_id = planning.write.record.id

        assert planning.write.created is True
        assert planning.write.event_id is not None
        assert planning.write.record.status == "planned"
        assert planning.requested_attempt_number == 1

        assert planning.request.source.objective.namespace == (
            "customer_service.support"
        )
        assert (
            planning.request.source.objective.objective_ref
            == (lineage["review_plan_id"])
        )
        assert planning.plan.automatic_execution_allowed is False
        assert planning.plan.human_approval_required is True

        assert (
            planning.canonical_review_plan.resolution_record_id
            == lineage["resolution_record_id"]
        )
        assert (
            planning.canonical_review_plan.review_plan_id == lineage["review_plan_id"]
        )
        assert (
            planning.canonical_review_plan.support_outcome_id
            == lineage["support_outcome_id"]
        )
        assert (
            planning.canonical_review_plan.workflow_run_id
            == lineage["source_workflow_run_id"]
        )

        launch_jobs = await HELPERS.jobs_for_user(
            db,
            user_id=user_id,
            job_type=(CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB),
        )

        assert len(launch_jobs) == 1

        launch_job_id = launch_jobs[0].id

        assert launch_jobs[0].status == "queued"
        assert launch_jobs[0].payload["repair_execution_id"] == str(repair_execution_id)

        # -----------------------------------------------------
        # 4. Replay the same delegation while the repair is
        #    still in its original planned lifecycle state.
        #
        #    The durable identity and immutable planning facts
        #    still match, so the command must converge without
        #    another event or launch job.
        # -----------------------------------------------------

        replay_before_launch = await CustomerSupportRepairPlanningCoordinator(db).plan(
            decision=delegation,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert replay_before_launch.write.created is False
        assert replay_before_launch.write.event_id is None
        assert replay_before_launch.write.record.id == (repair_execution_id)
        assert replay_before_launch.write.record.status == "planned"
        assert replay_before_launch.requested_attempt_number == 1

        launch_jobs_after_planned_replay = await HELPERS.jobs_for_user(
            db,
            user_id=user_id,
            job_type=(CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB),
        )

        assert len(launch_jobs_after_planned_replay) == 1
        assert launch_jobs_after_planned_replay[0].id == launch_job_id

        repair_rows_before_launch = list(
            (
                await db.execute(
                    select(ObjectiveRepairExecutionRecord).where(
                        ObjectiveRepairExecutionRecord.user_id == user_id,
                        ObjectiveRepairExecutionRecord.resolution_record_id
                        == lineage["resolution_record_id"],
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(repair_rows_before_launch) == 1
        assert repair_rows_before_launch[0].id == repair_execution_id
        assert repair_rows_before_launch[0].status == "planned"

    # ---------------------------------------------------------
    # 5. Run the real product launch job. It must load the
    #    canonical plan, build the workflow, create workflow.run,
    #    and transition the repair execution to queued.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        completed_launch_job = await JobWorker(
            db,
            worker_id=f"slice-6d-launch-{uuid4()}",
        ).run_once(
            job_id=launch_job_id,
        )

        assert completed_launch_job is not None
        assert completed_launch_job.status == "succeeded"

        repair = await HELPERS.repair_for_user(
            db,
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        assert repair.status == "queued"
        assert repair.workflow_job_id is not None
        assert repair.workflow_json is not None
        assert repair.workflow_run_id is None

        workflow_job_id = repair.workflow_job_id

        workflow_job = await db.get(
            PlatformJob,
            workflow_job_id,
        )

        assert workflow_job is not None
        assert workflow_job.job_type == "workflow.run"
        assert workflow_job.status == "queued"

        objective_repair = workflow_job.payload["extras"]["objective_repair"]

        assert objective_repair["repair_execution_id"] == str(repair_execution_id)
        assert objective_repair["resolution_record_id"] == str(
            lineage["resolution_record_id"]
        )
        assert objective_repair["attempt_number"] == 1

    # ---------------------------------------------------------
    # 6. The original planning command is now stale.
    #
    #    Launch advanced durable lifecycle truth from planned
    #    to queued. Replaying the original planned-state facts
    #    must conflict rather than overwrite or move the repair
    #    backward.
    # ---------------------------------------------------------

    async with SessionLocal() as db:
        with pytest.raises(
            ObjectiveRepairExecutionConflictError,
            match=("already exists with different facts: status"),
        ):
            await CustomerSupportRepairPlanningCoordinator(db).plan(
                decision=delegation,
                user_id=user_id,
                tenant_id=tenant_id,
            )

        # The coordinator rolls back on error, but an explicit
        # rollback keeps the test transaction state unambiguous.
        await db.rollback()

        persisted_repair = await HELPERS.repair_for_user(
            db,
            user_id=user_id,
            repair_execution_id=(repair_execution_id),
        )

        assert persisted_repair.status == "queued"
        assert persisted_repair.workflow_job_id == (workflow_job_id)

        launch_jobs_after_stale_replay = await HELPERS.jobs_for_user(
            db,
            user_id=user_id,
            job_type=(CUSTOMER_SUPPORT_OBJECTIVE_REPAIR_LAUNCH_JOB),
        )

        assert len(launch_jobs_after_stale_replay) == 1
        assert launch_jobs_after_stale_replay[0].id == launch_job_id

        workflow_jobs_after_stale_replay = await HELPERS.jobs_for_user(
            db,
            user_id=user_id,
            job_type="workflow.run",
        )

        assert len(workflow_jobs_after_stale_replay) == 1
        assert workflow_jobs_after_stale_replay[0].id == workflow_job_id

        repair_rows = list(
            (
                await db.execute(
                    select(ObjectiveRepairExecutionRecord).where(
                        ObjectiveRepairExecutionRecord.user_id == user_id,
                        ObjectiveRepairExecutionRecord.resolution_record_id
                        == lineage["resolution_record_id"],
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(repair_rows) == 1
        assert repair_rows[0].id == (repair_execution_id)
        assert repair_rows[0].status == "queued"
