from __future__ import annotations

# ============================================================
# Legacy HTTP source: app/domains/customer_service/routers/objective_learning.py
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
from app.domains.customer_service.schemas.objective_learning import (
    ObjectiveLearningApprovedInsightListResponse,
    ObjectiveLearningCandidateGenerateRequest,
    ObjectiveLearningCandidateListResponse,
    ObjectiveLearningExperienceListResponse,
    ObjectiveLearningExperienceRead,
    ObjectiveLearningPolicyEnsureRequest,
    ObjectiveLearningPolicyEnsureResponse,
    ObjectiveLearningPolicyRevisionListResponse,
    ObjectiveLearningPolicyRevisionRead,
)
from app.domains.customer_service.security.rbac import (
    get_customer_service_principal as get_current_user,
)
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_candidate_generation import (
    CustomerSupportObjectiveLearningCandidateGenerationResult,
)
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_durable_policy_generation import (
    CustomerSupportObjectiveLearningDurablePolicyGenerationService,
    CustomerSupportObjectiveLearningPolicyNotFoundError,
)
from app.domains.customer_service.services.support.learning.customer_support_objective_learning_policy_bootstrap import (
    CustomerSupportObjectiveLearningPolicyBootstrapService,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF,
    CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
    CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningAggregation,
    ObjectiveLearningApprovedInsight,
    ObjectiveLearningApprovedInsightService,
    ObjectiveLearningCandidate,
    ObjectiveLearningCandidateReviewRequest,
    ObjectiveLearningExperienceRepository,
    ObjectiveLearningLifecycleOperations,
    ObjectiveLearningPolicyRepository,
    ObjectiveLearningPolicyScope,
    ObjectiveLearningSummaryService,
)

objective_learning_router = APIRouter(
    prefix="/objective-learning",
    tags=["Customer Service - Objective Learning"],
)


def _customer_support_policy_scope(
    *,
    user_id: UUID,
    tenant_id: str | None,
) -> ObjectiveLearningPolicyScope:
    return ObjectiveLearningPolicyScope(
        user_id=user_id,
        tenant_id=tenant_id,
        objective_namespace=CUSTOMER_SUPPORT_OBJECTIVE_NAMESPACE,
        objective_type=CUSTOMER_SUPPORT_OBJECTIVE_TYPE,
        profile_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_PROFILE_REF),
        policy_ref=(CUSTOMER_SUPPORT_OBJECTIVE_LEARNING_POLICY_REF),
    )


@objective_learning_router.post(
    "/policies/current",
    response_model=ObjectiveLearningPolicyEnsureResponse,
    status_code=201,
)
async def ensure_current_objective_learning_policy(
    payload: ObjectiveLearningPolicyEnsureRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningPolicyEnsureResponse:
    """
    Ensure the current server-owned customer-support learning policy.

    The request cannot alter policy identity, thresholds, versions, safety
    controls, planning, ranking, provider selection, workflow behavior, or
    execution authorization.
    """

    try:
        result = await CustomerSupportObjectiveLearningPolicyBootstrapService(
            db
        ).ensure_current(
            user_id=current_user.id,
            tenant_id=payload.tenant_id,
        created_by_user_id=getattr(current_user, "actor_user_id", current_user.id),
        )

        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return ObjectiveLearningPolicyEnsureResponse(
        revision=ObjectiveLearningPolicyRevisionRead(
            **result.revision.model_dump(mode="python")
        ),
        created=result.created,
    )


@objective_learning_router.get(
    "/policies/current",
    response_model=ObjectiveLearningPolicyRevisionRead,
)
async def get_current_objective_learning_policy(
    tenant_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningPolicyRevisionRead:
    scope = _customer_support_policy_scope(
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    repository = ObjectiveLearningPolicyRepository(db)

    record = await repository.get_latest_for_scope(
        scope=scope,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Objective learning policy not found",
        )

    return ObjectiveLearningPolicyRevisionRead.from_record(record)


@objective_learning_router.get(
    "/policies",
    response_model=ObjectiveLearningPolicyRevisionListResponse,
)
async def list_objective_learning_policy_revisions(
    tenant_id: str | None = Query(default=None),
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
) -> ObjectiveLearningPolicyRevisionListResponse:
    scope = _customer_support_policy_scope(
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    records = await ObjectiveLearningPolicyRepository(db).list_revisions(
        scope=scope,
        limit=limit,
        offset=offset,
    )

    items = tuple(
        ObjectiveLearningPolicyRevisionRead.from_record(record) for record in records
    )

    return ObjectiveLearningPolicyRevisionListResponse(
        items=items,
        count=len(items),
        limit=limit,
        offset=offset,
    )


@objective_learning_router.get(
    "/policies/{policy_version}",
    response_model=ObjectiveLearningPolicyRevisionRead,
)
async def get_objective_learning_policy_revision(
    policy_version: int,
    tenant_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningPolicyRevisionRead:
    if policy_version < 1:
        raise HTTPException(
            status_code=422,
            detail="policy_version must be >= 1",
        )

    scope = _customer_support_policy_scope(
        user_id=current_user.id,
        tenant_id=tenant_id,
    )

    record = await ObjectiveLearningPolicyRepository(db).get_revision_for_scope(
        scope=scope,
        policy_version=policy_version,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Objective learning policy revision not found",
        )

    return ObjectiveLearningPolicyRevisionRead.from_record(record)


@objective_learning_router.get(
    "/experiences/{experience_id}",
    response_model=ObjectiveLearningExperienceRead,
)
async def get_objective_learning_experience(
    experience_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningExperienceRead:
    record = await ObjectiveLearningExperienceRepository(db).get_for_user(
        user_id=current_user.id,
        record_id=experience_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=("Objective learning experience not found"),
        )

    return ObjectiveLearningExperienceRead.from_record(record)


@objective_learning_router.get(
    "/resolutions/{resolution_record_id}/experiences",
    response_model=ObjectiveLearningExperienceListResponse,
)
async def list_objective_learning_experiences_for_resolution(
    resolution_record_id: UUID,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningExperienceListResponse:
    records = await ObjectiveLearningExperienceRepository(db).list_for_resolution(
        user_id=current_user.id,
        resolution_record_id=resolution_record_id,
        limit=limit,
    )

    items = tuple(
        ObjectiveLearningExperienceRead.from_record(record) for record in records
    )

    return ObjectiveLearningExperienceListResponse(
        items=items,
        count=len(items),
    )


@objective_learning_router.get(
    "/summaries",
    response_model=list[ObjectiveLearningAggregation],
)
async def list_objective_learning_summaries(
    window_hours: int = Query(
        default=720,
        ge=1,
        le=8760,
    ),
    tenant_id: str | None = Query(default=None),
    objective_namespace: str | None = Query(default=None),
    objective_type: str | None = Query(default=None),
    objective_version: int | None = Query(
        default=None,
        ge=1,
    ),
    schema_ref: str | None = Query(default=None),
    profile_ref: str | None = Query(default=None),
    profile_version: int | None = Query(
        default=None,
        ge=1,
    ),
    extractor_ref: str | None = Query(default=None),
    extractor_version: int | None = Query(
        default=None,
        ge=1,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ObjectiveLearningAggregation]:
    try:
        return await ObjectiveLearningSummaryService(db).summarize(
            user_id=current_user.id,
            window_hours=window_hours,
            tenant_id=tenant_id,
            objective_namespace=objective_namespace,
            objective_type=objective_type,
            objective_version=objective_version,
            schema_ref=schema_ref,
            profile_ref=profile_ref,
            profile_version=profile_version,
            extractor_ref=extractor_ref,
            extractor_version=extractor_version,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@objective_learning_router.post(
    "/candidates/generate",
    response_model=(CustomerSupportObjectiveLearningCandidateGenerationResult),
    status_code=201,
)
async def generate_objective_learning_candidates(
    payload: ObjectiveLearningCandidateGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CustomerSupportObjectiveLearningCandidateGenerationResult:
    """
    Explicitly generate reviewable customer-support candidates.

    This authenticated operation summarizes immutable evidence and
    persists advisory candidates only. It does not activate guidance,
    alter ranking or planning, select capabilities or providers,
    change runtime policy, bypass approval or verification, or
    authorize execution.
    """

    try:
        return await CustomerSupportObjectiveLearningDurablePolicyGenerationService(
            db
        ).generate(
            user_id=current_user.id,
            tenant_id=payload.tenant_id,
            window_hours=payload.window_hours,
        )
    except CustomerSupportObjectiveLearningPolicyNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@objective_learning_router.get(
    "/candidates",
    response_model=ObjectiveLearningCandidateListResponse,
)
async def list_objective_learning_candidates(
    tenant_id: str | None = Query(default=None),
    objective_namespace: str | None = Query(default=None),
    objective_type: str | None = Query(default=None),
    objective_version: int | None = Query(
        default=None,
        ge=1,
    ),
    schema_ref: str | None = Query(default=None),
    profile_ref: str | None = Query(default=None),
    profile_version: int | None = Query(
        default=None,
        ge=1,
    ),
    extractor_ref: str | None = Query(default=None),
    extractor_version: int | None = Query(
        default=None,
        ge=1,
    ),
    status: str | None = Query(default=None),
    approval_status: str | None = Query(default=None),
    validation_passed: bool | None = Query(default=None),
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
) -> ObjectiveLearningCandidateListResponse:
    items = tuple(
        await ObjectiveLearningLifecycleOperations(db=db).list_latest(
            user_id=current_user.id,
            tenant_id=tenant_id,
            objective_namespace=objective_namespace,
            objective_type=objective_type,
            objective_version=objective_version,
            schema_ref=schema_ref,
            profile_ref=profile_ref,
            profile_version=profile_version,
            extractor_ref=extractor_ref,
            extractor_version=extractor_version,
            status=status,
            approval_status=approval_status,
            validation_passed=validation_passed,
            limit=limit,
            offset=offset,
        )
    )

    return ObjectiveLearningCandidateListResponse(
        items=items,
        count=len(items),
        limit=limit,
        offset=offset,
    )


@objective_learning_router.get(
    "/candidates/{candidate_id}",
    response_model=ObjectiveLearningCandidate,
)
async def get_objective_learning_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningCandidate:
    candidate = await ObjectiveLearningLifecycleOperations(db=db).get_latest(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=("Objective learning candidate not found"),
        )

    return candidate


@objective_learning_router.get(
    "/candidates/{candidate_id}/history",
    response_model=list[ObjectiveLearningCandidate],
)
async def list_objective_learning_candidate_history(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ObjectiveLearningCandidate]:
    lifecycle = ObjectiveLearningLifecycleOperations(db=db)

    candidate = await lifecycle.get_latest(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=("Objective learning candidate not found"),
        )

    return await lifecycle.history(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )


@objective_learning_router.get(
    "/approved-insights",
    response_model=(ObjectiveLearningApprovedInsightListResponse),
)
async def list_objective_learning_approved_insights(
    tenant_id: str | None = Query(default=None),
    objective_namespace: str | None = Query(default=None),
    objective_type: str | None = Query(default=None),
    objective_version: int | None = Query(
        default=None,
        ge=1,
    ),
    schema_ref: str | None = Query(default=None),
    profile_ref: str | None = Query(default=None),
    profile_version: int | None = Query(
        default=None,
        ge=1,
    ),
    extractor_ref: str | None = Query(default=None),
    extractor_version: int | None = Query(
        default=None,
        ge=1,
    ),
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
) -> ObjectiveLearningApprovedInsightListResponse:
    items = tuple(
        await ObjectiveLearningApprovedInsightService(db=db).list_approved(
            user_id=current_user.id,
            tenant_id=tenant_id,
            objective_namespace=objective_namespace,
            objective_type=objective_type,
            objective_version=objective_version,
            schema_ref=schema_ref,
            profile_ref=profile_ref,
            profile_version=profile_version,
            extractor_ref=extractor_ref,
            extractor_version=extractor_version,
            limit=limit,
            offset=offset,
        )
    )

    return ObjectiveLearningApprovedInsightListResponse(
        items=items,
        count=len(items),
        limit=limit,
        offset=offset,
    )


@objective_learning_router.get(
    "/approved-insights/{candidate_id}",
    response_model=ObjectiveLearningApprovedInsight,
)
async def get_objective_learning_approved_insight(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningApprovedInsight:
    insight = await ObjectiveLearningApprovedInsightService(db=db).get_approved(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if insight is None:
        raise HTTPException(
            status_code=404,
            detail=("Approved objective learning insight not found"),
        )

    return insight


@objective_learning_router.post(
    "/candidates/{candidate_id}/reviews",
    response_model=ObjectiveLearningCandidate,
)
async def review_objective_learning_candidate(
    candidate_id: UUID,
    payload: ObjectiveLearningCandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ObjectiveLearningCandidate:
    """
    Append one authenticated human review revision.

    The review records advisory acceptance or rejection only.
    It does not activate guidance, alter ranking or planning,
    select providers, modify runtime policy, or authorize
    execution.
    """

    try:
        reviewed = await ObjectiveLearningLifecycleOperations(db=db).review(
            user_id=current_user.id,
            candidate_id=candidate_id,
        reviewed_by_user_id=getattr(current_user, "actor_user_id", current_user.id),
            request=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    if reviewed is None:
        raise HTTPException(
            status_code=404,
            detail=("Objective learning candidate not found"),
        )

    return reviewed


__all__ = [
    "objective_learning_router",
]
