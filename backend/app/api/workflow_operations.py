from __future__ import annotations


# ============================================================
# app/workflow_operations/waits/router.py
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.api.auth import get_current_user
from app.workflow_operations.waits.schemas import (
    WorkflowWaitCreate,
    WorkflowWaitRead,
    WorkflowWaitResolve,
)
from app.workflow_operations.waits.scheduler import WorkflowWaitScheduler
from app.workflow_operations.waits.service import WorkflowWaitService
from app.workflow_operations.snapshots.schemas import WorkflowRunSnapshotRead
from app.workflow_operations.snapshots.service import WorkflowSnapshotService
from app.workflow_operations.snapshots.replay import WorkflowReplayService
from app.workflow_operations.timeline.service import WorkflowTimelineService
from app.workflow_operations.diff.snapshot_compare import (
    WorkflowSnapshotCompareService,
)
from app.workflow_operations.diff.run_compare import WorkflowRunCompareService
from app.workflow_operations.evaluations.schemas import (
    WorkflowEvaluationRequest,
    WorkflowEvaluationResult,
)
from app.workflow_operations.evaluations.service import WorkflowEvaluationService
from app.workflow_operations.evaluations.regression import (
    WorkflowRegressionCheckRequest,
    WorkflowRegressionCheckResult,
    WorkflowRegressionDetector,
)
from fastapi import HTTPException
from app.workflow_operations.versions.schemas import (
    WorkflowDefinitionCreate,
    WorkflowVersionCreate,
)
from app.workflow_operations.versions.service import WorkflowVersionService
from app.workflow_operations.metrics.service import WorkflowMetricsService
from app.workflow_operations.quality.schemas import (
    WorkflowDeploymentGateRequest,
    WorkflowDeploymentGateResult,
    WorkflowQualityInput,
    WorkflowQualityScore,
)
from app.workflow_operations.quality.service import WorkflowQualityService


workflow_waits_router = APIRouter(
    prefix="/workflow-waits",
    tags=["Workflow Waits"],
)


@workflow_waits_router.post("", response_model=WorkflowWaitRead)
async def create_wait(
    payload: WorkflowWaitCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowWaitService(db).create(
        user_id=current_user.id,
        payload=payload,
    )


@workflow_waits_router.get("", response_model=list[WorkflowWaitRead])
async def list_waits(
    status: str | None = Query(default=None),
    workflow_run_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowWaitService(db).list_for_user(
        user_id=current_user.id,
        status=status,
        workflow_run_id=workflow_run_id,
    )


@workflow_waits_router.post("/{wait_id}/resolve")
async def resolve_wait(
    wait_id: UUID,
    payload: WorkflowWaitResolve,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await WorkflowWaitService(db).resolve(
        user_id=current_user.id,
        wait_id=wait_id,
        resolution=payload.resolution,
        resume=payload.resume,
    )

    return {
        "wait": WorkflowWaitRead.model_validate(result["wait"]),
        "resume_job_id": result["resume_job_id"],
    }


@workflow_waits_router.post("/expire-due", response_model=list[WorkflowWaitRead])
async def expire_due_waits(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowWaitScheduler(db).expire_due(
        user_id=current_user.id,
    )


@workflow_waits_router.post("/{wait_id}/approve")
async def approve_workflow_wait(
    wait_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await WorkflowWaitService(db).approve(
        user_id=current_user.id,
        wait_id=wait_id,
    )

    return {
        "wait_id": str(result["wait"].id),
        "status": result["wait"].status,
        "workflow_run_id": result["wait"].workflow_run_id,
        "resume_job_id": str(result["resume_job"].id)
        if result.get("resume_job")
        else None,
        "approved": True,
    }


@workflow_waits_router.post("/{wait_id}/reject")
async def reject_workflow_wait(
    wait_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await WorkflowWaitService(db).reject(
        user_id=current_user.id,
        wait_id=wait_id,
    )

    return {
        "wait_id": str(result["wait"].id),
        "status": result["wait"].status,
        "workflow_run_id": result["wait"].workflow_run_id,
        "resume_job_id": str(result["resume_job"].id)
        if result.get("resume_job")
        else None,
        "approved": False,
    }


# ============================================================
# app/workflow_operations/snapshots/router.py
# ============================================================





workflow_snapshots_router = APIRouter(
    prefix="/workflow-snapshots",
    tags=["Workflow Snapshots"],
)


@workflow_snapshots_router.get(
    "/runs/{workflow_run_id}", response_model=list[WorkflowRunSnapshotRead]
)
async def list_run_snapshots(
    workflow_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowSnapshotService(db).list_for_run(
        workflow_run_id=workflow_run_id,
        user_id=current_user.id,
    )


@workflow_snapshots_router.get("/{snapshot_id}", response_model=WorkflowRunSnapshotRead)
async def get_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowSnapshotService(db).get_or_404(
        snapshot_id=snapshot_id,
        user_id=current_user.id,
    )


@workflow_snapshots_router.post("/{snapshot_id}/replay")
async def replay_from_snapshot(
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await WorkflowReplayService(db).create_replay_job(
        user_id=current_user.id,
        snapshot_id=snapshot_id,
    )

    return {
        "snapshot_id": str(result["snapshot"].id),
        "workflow_run_id": str(result["snapshot"].workflow_run_id),
        "job_id": str(result["job"].id),
        "job_type": result["job"].job_type,
        "status": result["job"].status,
    }


# ============================================================
# app/workflow_operations/timeline/router.py
# ============================================================





workflow_timeline_router = APIRouter(
    prefix="/workflows/runs",
    tags=["Workflow Timeline"],
)


@workflow_timeline_router.get("/{workflow_run_id}/timeline")
async def get_workflow_run_timeline(
    workflow_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowTimelineService(db).get_timeline(
        workflow_run_id=workflow_run_id,
        user_id=current_user.id,
    )


# ============================================================
# app/workflow_operations/diff/router.py
# ============================================================




workflow_diff_router = APIRouter(
    prefix="/workflow-diff",
    tags=["Workflow Diff"],
)


@workflow_diff_router.get("/snapshots/compare")
async def compare_snapshots(
    before_snapshot_id: UUID,
    after_snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowSnapshotCompareService(db).compare_snapshots(
        before_snapshot_id=before_snapshot_id,
        after_snapshot_id=after_snapshot_id,
        user_id=current_user.id,
    )


@workflow_diff_router.get("/runs/compare")
async def compare_runs(
    baseline_run_id: UUID,
    candidate_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await WorkflowRunCompareService(db).compare_runs(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        user_id=current_user.id,
    )

    if result.get("status") == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Workflow run snapshots not found",
        )

    return result


# ============================================================
# app/workflow_operations/evaluations/router.py
# ============================================================




workflow_evaluations_router = APIRouter(
    prefix="/workflow-evaluations",
    tags=["Workflow Evaluations"],
)


@workflow_evaluations_router.post("/run", response_model=WorkflowEvaluationResult)
async def run_workflow_evaluation(
    payload: WorkflowEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowEvaluationService(db).run_evaluation(
        user_id=current_user.id,
        request=payload,
    )


@workflow_evaluations_router.post(
    "/regression/check", response_model=WorkflowRegressionCheckResult
)
async def check_workflow_regression(
    payload: WorkflowRegressionCheckRequest,
    current_user=Depends(get_current_user),
):
    return WorkflowRegressionDetector().check(
        baseline=payload.baseline,
        candidate=payload.candidate,
        min_score_delta=payload.min_score_delta,
    )


# ============================================================
# app/workflow_operations/versions/router.py
# ============================================================





workflow_versions_router = APIRouter(
    prefix="/workflow-versions",
    tags=["Workflow Versions"],
)


@workflow_versions_router.post("/definitions")
async def create_definition(
    payload: WorkflowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowVersionService(db).create_definition(
        user_id=current_user.id,
        payload=payload,
    )


@workflow_versions_router.get("/definitions")
async def list_definitions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowVersionService(db).repo.list_definitions(
        user_id=current_user.id,
    )


@workflow_versions_router.post("/definitions/{definition_id}/versions")
async def create_version(
    definition_id: UUID,
    payload: WorkflowVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await WorkflowVersionService(db).create_version(
            definition_id=definition_id,
            user_id=current_user.id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@workflow_versions_router.get("/definitions/{definition_id}/versions")
async def list_versions(
    definition_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await WorkflowVersionService(db).list_versions(
            definition_id=definition_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@workflow_versions_router.post(
    "/definitions/{definition_id}/versions/{version}/publish"
)
async def publish_version(
    definition_id: UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await WorkflowVersionService(db).publish_version(
            definition_id=definition_id,
            user_id=current_user.id,
            version=version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@workflow_versions_router.post(
    "/definitions/{definition_id}/versions/{version}/rollback"
)
async def rollback_version(
    definition_id: UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await WorkflowVersionService(db).rollback(
            definition_id=definition_id,
            user_id=current_user.id,
            version=version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@workflow_versions_router.get("/definitions/{definition_id}/active")
async def get_active_version(
    definition_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        active = await WorkflowVersionService(db).get_active_version(
            definition_id=definition_id,
            user_id=current_user.id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if not active:
        raise HTTPException(status_code=404, detail="active_version_not_found")

    return active


# ============================================================
# app/workflow_operations/metrics/router.py
# ============================================================





workflow_metrics_router = APIRouter(
    prefix="/workflow-metrics",
    tags=["Workflow Metrics"],
)


@workflow_metrics_router.get("/runs")
async def list_run_metrics(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowMetricsService(db).repo.list_for_user(
        user_id=current_user.id,
        limit=limit,
    )


@workflow_metrics_router.get("/definitions/{definition_id}/versions/{version}/summary")
async def summarize_workflow_version_metrics(
    definition_id: UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await WorkflowMetricsService(db).summarize_version(
        user_id=current_user.id,
        workflow_definition_id=definition_id,
        workflow_version=version,
    )


# ============================================================
# app/workflow_operations/quality/router.py
# ============================================================




workflow_quality_router = APIRouter(
    prefix="/workflow-quality",
    tags=["Workflow Quality"],
)


@workflow_quality_router.post("/score", response_model=WorkflowQualityScore)
async def score_workflow_quality(
    payload: WorkflowQualityInput,
    current_user=Depends(get_current_user),
):
    return WorkflowQualityService().score(payload)


@workflow_quality_router.post(
    "/deployment-gate", response_model=WorkflowDeploymentGateResult
)
async def workflow_deployment_gate(
    payload: WorkflowDeploymentGateRequest,
    current_user=Depends(get_current_user),
):
    return WorkflowQualityService().deployment_gate(payload)


__all__ = [
    "workflow_waits_router",
    "workflow_snapshots_router",
    "workflow_timeline_router",
    "workflow_diff_router",
    "workflow_evaluations_router",
    "workflow_versions_router",
    "workflow_metrics_router",
    "workflow_quality_router",
]
