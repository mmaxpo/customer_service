from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/analytics.py
# ============================================================
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.domains.customer_service.schemas.analytics import (
    CustomerServiceAnalytics,
    WorkloadReportItem,
)
from app.domains.customer_service.schemas.workload import WorkloadReport
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
    require_customer_service_permission,
)
from app.domains.customer_service.services.analytics import AnalyticsService
from app.runtime.learning import (
    BusinessLearningAggregationPolicy,
    BusinessLearningApprovalStatus,
    BusinessLearningApprovedInsight,
    BusinessLearningApprovedInsightService,
    BusinessLearningCandidateGenerateRequest,
    BusinessLearningCandidateGenerationResult,
    BusinessLearningCandidateReviewRequest,
    BusinessLearningCandidateStatus,
    BusinessLearningInsightCandidate,
    BusinessLearningInsightCandidateOperations,
    BusinessLearningSummary,
    BusinessLearningSummaryService,
    BusinessLearningTrendPolicy,
    BusinessLearningTrendReport,
    BusinessLearningTrendService,
)
from app.domains.customer_service.services.dashboard import (
    CustomerServiceDashboardService,
)
from app.domains.customer_service.schemas.reply_quality_insights import (
    ReplyQualityInsightsRead,
)
from app.domains.customer_service.services.reply_quality_insights import (
    ReplyQualityInsightsService,
)
from app.domains.customer_service.schemas.reply_quality_dashboard import (
    ReplyQualityDashboardRead,
)
from app.domains.customer_service.services.reply_quality_dashboard import (
    ReplyQualityDashboardService,
)
from app.domains.customer_service.services.reply_quality_trends import (
    ReplyQualityTrendsService,
)
from app.domains.customer_service.schemas.audit_logs import AuditLogRead
from app.domains.customer_service.services.audit_logs import AuditLogService

analytics_router = APIRouter(
    tags=["Customer Service - Analytics"],
    dependencies=[Depends(require_customer_service_permission("cs.analytics.read"))],
)


@analytics_router.get("/", response_model=CustomerServiceAnalytics)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await AnalyticsService(db).get_summary(current_user.id)


@analytics_router.get("/workload", response_model=list[WorkloadReportItem])
async def workload_report(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await AnalyticsService(db).workload(current_user.id)


@analytics_router.get("/workload-report", response_model=WorkloadReport)
async def workload_visibility_report(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await AnalyticsService(db).workload_report(current_user.id)


@analytics_router.get(
    "/business-learning/summary",
    response_model=list[BusinessLearningSummary],
)
async def business_learning_summary(
    window_hours: int = Query(
        default=720,
        ge=1,
        le=8760,
    ),
    tenant_id: str | None = Query(default=None),
    objective_namespace: str | None = Query(default=None),
    objective_type: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    minimum_effective_sample_size: float = Query(
        default=5.0,
        ge=0.1,
        le=100000.0,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = BusinessLearningSummaryService(
        db,
        policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=(minimum_effective_sample_size)
            )
        ),
    )

    return await service.summarize(
        user_id=current_user.id,
        window_hours=window_hours,
        tenant_id=tenant_id,
        objective_namespace=(objective_namespace),
        objective_type=objective_type,
        decision=decision,
    )


@analytics_router.get(
    "/business-learning/trends",
    response_model=list[BusinessLearningTrendReport],
)
async def business_learning_trends(
    window_hours: int = Query(
        default=168,
        ge=1,
        le=4380,
    ),
    tenant_id: str | None = Query(default=None),
    objective_namespace: str | None = Query(default=None),
    objective_type: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    minimum_effective_sample_size: float = Query(
        default=5.0,
        ge=0.1,
        le=100000.0,
    ),
    meaningful_success_delta: float = Query(
        default=0.10,
        ge=0.0,
        le=1.0,
    ),
    meaningful_failure_delta: float = Query(
        default=0.10,
        ge=0.0,
        le=1.0,
    ),
    contradiction_threshold: float = Query(
        default=0.60,
        ge=0.0,
        le=1.0,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = BusinessLearningTrendService(
        db,
        aggregation_policy=(
            BusinessLearningAggregationPolicy(
                minimum_effective_sample_size=(minimum_effective_sample_size)
            )
        ),
        trend_policy=(
            BusinessLearningTrendPolicy(
                meaningful_success_delta=(meaningful_success_delta),
                meaningful_failure_delta=(meaningful_failure_delta),
                contradiction_threshold=(contradiction_threshold),
            )
        ),
    )

    return await service.analyze(
        user_id=current_user.id,
        window_hours=window_hours,
        tenant_id=tenant_id,
        objective_namespace=(objective_namespace),
        objective_type=objective_type,
        decision=decision,
    )


@analytics_router.post(
    "/business-learning/insight-candidates/generate",
    response_model=(BusinessLearningCandidateGenerationResult),
    status_code=201,
)
async def generate_business_learning_candidates(
    request: BusinessLearningCandidateGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await BusinessLearningInsightCandidateOperations(db).generate(
            user_id=current_user.id,
            request=request,
        )
    except ValueError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@analytics_router.get(
    "/business-learning/insight-candidates",
    response_model=dict,
)
async def list_business_learning_candidates(
    tenant_id: str | None = Query(default=None),
    objective_namespace: str | None = Query(default=None),
    objective_type: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    status: (BusinessLearningCandidateStatus | None) = Query(default=None),
    approval_status: (BusinessLearningApprovalStatus | None) = Query(default=None),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = await BusinessLearningInsightCandidateOperations(db).list_latest(
        user_id=current_user.id,
        tenant_id=tenant_id,
        objective_namespace=(objective_namespace),
        objective_type=objective_type,
        decision=decision,
        status=(status.value if status is not None else None),
        approval_status=(
            approval_status.value if approval_status is not None else None
        ),
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [item.model_dump(mode="json") for item in items],
    }


@analytics_router.get(
    "/business-learning/insight-candidates/{candidate_id}/history",
    response_model=list[BusinessLearningInsightCandidate],
)
async def get_business_learning_candidate_history(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = await BusinessLearningInsightCandidateOperations(db).history(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if not items:
        raise HTTPException(
            status_code=404,
            detail=("Business-learning insight candidate not found"),
        )

    return items


@analytics_router.get(
    "/business-learning/insight-candidates/{candidate_id}",
    response_model=BusinessLearningInsightCandidate,
)
async def get_business_learning_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    candidate = await BusinessLearningInsightCandidateOperations(db).get_latest(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=("Business-learning insight candidate not found"),
        )

    return candidate


@analytics_router.post(
    "/business-learning/insight-candidates/{candidate_id}/review",
    response_model=BusinessLearningInsightCandidate,
)
async def review_business_learning_candidate(
    candidate_id: UUID,
    request: BusinessLearningCandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        candidate = await BusinessLearningInsightCandidateOperations(db).review(
            user_id=current_user.id,
            candidate_id=candidate_id,
        reviewed_by_user_id=getattr(current_user, "actor_user_id", current_user.id),
            request=request,
        )
    except ValueError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=("Business-learning insight candidate not found"),
        )

    return candidate


@analytics_router.get(
    "/business-learning/approved-insights",
    response_model=dict,
)
async def list_business_learning_approved_insights(
    tenant_id: str | None = Query(default=None),
    objective_namespace: str | None = Query(default=None),
    objective_type: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = await BusinessLearningApprovedInsightService(db).list_approved(
        user_id=current_user.id,
        tenant_id=tenant_id,
        objective_namespace=(objective_namespace),
        objective_type=objective_type,
        decision=decision,
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [item.model_dump(mode="json") for item in items],
    }


@analytics_router.get(
    "/business-learning/approved-insights/{candidate_id}",
    response_model=BusinessLearningApprovedInsight,
)
async def get_business_learning_approved_insight(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    insight = await BusinessLearningApprovedInsightService(db).get_approved(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if insight is None:
        raise HTTPException(
            status_code=404,
            detail=("Approved business-learning insight not found"),
        )

    return insight


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/dashboard.py
# ============================================================



dashboard_router = APIRouter(tags=["Customer Service - Dashboard"])


@dashboard_router.get("/dashboard")
async def get_dashboard_aggregates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await CustomerServiceDashboardService(db).aggregates(
        user_id=current_user.id,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/reply_quality_insights.py
# ============================================================



reply_quality_insights_router = APIRouter(
    tags=["Customer Service - Reply Quality Insights"]
)


@reply_quality_insights_router.get(
    "/analytics/reply-quality/insights",
    response_model=ReplyQualityInsightsRead,
)
async def reply_quality_insights(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ReplyQualityInsightsService(db).get_insights(
        user_id=current_user.id,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/reply_quality_dashboard.py
# ============================================================



reply_quality_dashboard_router = APIRouter(
    tags=["Customer Service - Reply Quality Dashboard"]
)


@reply_quality_dashboard_router.get(
    "/analytics/reply-quality/dashboard",
    response_model=ReplyQualityDashboardRead,
)
async def reply_quality_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ReplyQualityDashboardService(db).dashboard(user_id=current_user.id)


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/reply_quality_trends.py
# ============================================================



reply_quality_trends_router = APIRouter(
    tags=["Customer Service - Reply Quality Trends"]
)


@reply_quality_trends_router.get("/analytics/reply-quality/trends")
async def reply_quality_trends(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await ReplyQualityTrendsService(db).get_trends(
        user_id=current_user.id,
    )


# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/audit_logs.py
# ============================================================



audit_logs_router = APIRouter(
    prefix="/audit-logs", tags=["Customer Service - Audit Logs"]
)


@audit_logs_router.get("/", response_model=list[AuditLogRead])
async def list_audit_logs(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await AuditLogService(db).list_logs(
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )


__all__ = [
    "analytics_router",
    "dashboard_router",
    "reply_quality_insights_router",
    "reply_quality_dashboard_router",
    "reply_quality_trends_router",
    "audit_logs_router",
]
