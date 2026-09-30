from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.session import get_db
from app.domains.customer_service.repositories.shopify import ShopifyRepository
from app.domains.customer_service.services.shopify_provider_installation import (
    ShopifyProviderInstallationProjector,
)
from app.domains.customer_service.services.shopify_provider_lifecycle import (
    ShopifyProviderLifecycleEvents,
)
from app.domains.customer_service.services.shopify_provider_verification import (
    register_shopify_provider_verifier,
)
from app.runtime.capabilities.execution.health.control import (
    CapabilityProviderHealthControlService,
)
from app.runtime.capabilities.execution.health.decisions import ProviderHealthState
from app.runtime.capabilities.execution.health.repository import (
    CapabilityProviderHealthRepository,
)
from app.runtime.capabilities.execution.installation.history import (
    ProviderInstallationHistoryQuery,
    sanitize_provider_installation_event,
)
from app.runtime.capabilities.execution.installation.operations import (
    CapabilityProviderInstallationOperations,
)
from app.runtime.capabilities.execution.installation.repository import (
    CapabilityProviderInstallationRepository,
)
from app.runtime.capabilities.execution.installation.verification import (
    ProviderInstallationVerifierRegistry,
    UnsupportedProviderVerificationError,
)
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningAggregationPolicy,
    CapabilityLearningApprovalStatus,
    CapabilityLearningCandidateGenerateRequest,
    CapabilityLearningCandidateGenerationResult,
    CapabilityLearningCandidateReviewRequest,
    CapabilityLearningCandidateStatus,
    CapabilityLearningInsightCandidate,
    CapabilityLearningInsightCandidateOperations,
    CapabilityLearningInsightPromotion,
    CapabilityLearningInsightPromotionOperations,
    CapabilityLearningObservationRepository,
    CapabilityLearningPromotionCreateRequest,
    CapabilityLearningPromotionRevokeRequest,
    CapabilityLearningPromotionStatus,
    CapabilityLearningPromotionTarget,
    CapabilityLearningSummary,
    CapabilityLearningSummaryService,
    CapabilityLearningTrendPolicy,
    CapabilityLearningTrendReport,
    CapabilityLearningTrendService,
)
from app.runtime.capabilities.execution.performance.queries import (
    CapabilityPerformanceQueryRepository,
)
from app.runtime.capabilities.execution.performance.reliability import (
    CapabilityProviderReliabilityReport,
    CapabilityReliabilityPolicy,
)
from app.runtime.capabilities.execution.performance.reliability_service import (
    CapabilityReliabilityService,
)
from app.runtime.capabilities.execution.policy.models import (
    CapabilityRuntimePolicy,
    CapabilityRuntimePolicyPatch,
    CapabilityRuntimePolicyScope,
)
from app.runtime.capabilities.execution.policy.operations import (
    CapabilityRuntimePolicyOperations,
)
from app.runtime.capabilities.execution.policy.repository import (
    CapabilityRuntimePolicyRepository,
    DatabaseCapabilityRuntimePolicyReader,
)
from app.runtime.capabilities.execution.verification import (
    TaskVerificationRepository,
    TaskVerificationRequest,
)
from app.runtime_services import build_application_runtime_services
from app.tcos.capabilities.models import CapabilityDefinition
from app.tcos.capabilities.planner import CapabilityMatchRequest, match_capabilities
from app.tcos.capabilities.planner_advisory_composition import (
    CapabilityAdvisoryMatchRequest,
    CapabilityAdvisoryMatchResponse,
    CapabilityPlannerAdvisoryComposer,
)
from app.tcos.capabilities.repository import CapabilityMetadataRepository
from app.tcos.capabilities.service import (
    build_capability_registry,
    build_capability_registry_for_tenant,
)

# ============================================================
# HTTP transport schemas
# ============================================================


class CapabilityRead(CapabilityDefinition):
    pass


class CapabilityMetadataUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str
    tenant_id: UUID | None = None
    display_name: str | None = None
    description: str | None = None
    domain: str | None = None
    category: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)
    is_enabled: bool = True


class CapabilityMetadataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    capability_id: str
    tenant_id: UUID | None = None
    display_name: str | None = None
    description: str | None = None
    domain: str | None = None
    category: str | None = None
    status: str | None = None
    tags: list[str]
    extra: dict
    is_enabled: bool


class CapabilityPerformanceObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_event_id: UUID
    correlation_id: str
    attempt_index: int

    requested_capability_id: str
    resolved_capability_id: str | None = None

    provider_id: str | None = None
    provider_ref: str | None = None

    status: str
    succeeded: bool

    duration_ms: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    failure_kind: str | None = None
    exception_type: str | None = None

    fallback_allowed: bool
    fallback_used: bool
    final_attempt: bool

    tenant_id: str | None = None
    workflow_run_id: str | None = None
    planner_session_id: str | None = None
    thread_id: str | None = None

    observed_at: datetime
    created_at: datetime


class CapabilityLearningObservationRead(BaseModel):
    """
    Public representation of immutable verified learning evidence.

    Raw verification inputs, execution output, and evidence data are
    intentionally not exposed.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    source_event_id: UUID
    source_verification_record_id: UUID

    verification_id: str
    attempt_number: int

    user_id: UUID
    tenant_id: str | None = None

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    outcome: str
    method: str
    reason_code: str
    confidence: float

    retryable: bool
    is_final: bool

    correlation_id: str | None = None
    workflow_run_id: str | None = None
    task_id: str | None = None

    summary: str

    observed_outcome_json: dict
    evidence_summary_json: dict
    context_json: dict

    observed_at: datetime
    created_at: datetime


class CapabilityProviderHealthStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tenant_id: str | None = None
    capability_id: str
    provider_id: str
    provider_ref: str | None = None

    current_state: str
    effective_state: str

    qualifying_recommendation: str | None = None
    qualifying_windows: int
    cooldown_until: datetime | None = None

    manual_override_state: str | None = None
    manual_override_reason: str | None = None
    manual_override_until: datetime | None = None
    override_active: bool

    version: int
    last_evaluated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CapabilityProviderHealthDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    state_id: UUID
    decision_key: str

    tenant_id: str | None = None
    capability_id: str
    provider_id: str
    provider_ref: str | None = None

    previous_state: str
    proposed_state: str
    resulting_state: str

    action: str
    reason: str
    evidence_recommendation: str
    evidence_sufficient: bool

    qualifying_windows: int
    required_windows: int

    window_start: datetime
    window_end: datetime
    evaluated_at: datetime
    cooldown_until: datetime | None = None

    evidence_json: dict
    explanation: str
    state_version: int
    created_at: datetime


class CapabilityProviderHealthOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    capability_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    provider_ref: str | None = None

    override_state: str = Field(pattern="^(healthy|degraded|unhealthy|recovering)$")
    reason: str = Field(min_length=1, max_length=2000)
    override_until: datetime | None = None


class CapabilityRuntimePolicyRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None

    enabled: bool = True
    policy_payload: CapabilityRuntimePolicyPatch
    reason: str | None = Field(
        default=None,
        max_length=2000,
    )


class CapabilityRuntimePolicyRevisionRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    policy_key: str
    scope_key: str

    user_id: UUID
    tenant_id: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None

    version: int
    enabled: bool
    policy_payload: CapabilityRuntimePolicyPatch

    reason: str | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime


class CapabilityRuntimePolicyEffectiveRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool
    user_id: str | None = None
    tenant_id: str | None = None
    capability_id: str | None = None
    provider_id: str | None = None
    provider_ref: str | None = None

    effective_policy: CapabilityRuntimePolicy
    applied_revisions: tuple[
        CapabilityRuntimePolicyRevisionRead,
        ...,
    ] = ()
    resolution_reason: str


class CapabilityProviderInstallationRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    user_id: UUID
    tenant_id: str | None = None
    provider_id: str

    integration_kind: str
    integration_connection_id: str | None = None

    enabled: bool
    configuration_state: str
    authentication_state: str
    verification_state: str

    verified_at: datetime | None = None
    failure_code: str | None = None
    failure_message: str | None = None

    version: int
    metadata_json: dict

    created_at: datetime
    updated_at: datetime


class CapabilityProviderInstallationEnabledUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    tenant_id: str | None = None
    enabled: bool


class CapabilityProviderInstallationReconcileRead(BaseModel):
    provider_id: str
    discovered: int
    projected: int
    items: list[CapabilityProviderInstallationRead]


class CapabilityProviderVerificationRead(BaseModel):
    provider_id: str
    ok: bool
    message: str
    installation: CapabilityProviderInstallationRead | None = None


class CapabilityProviderInstallationEventShopRead(BaseModel):
    id: str | int | None = None
    name: str | None = None
    myshopify_domain: str | None = None


class CapabilityProviderInstallationEventRead(BaseModel):
    id: UUID
    event_type: str
    source: str
    status: str

    provider_id: str
    installation_id: UUID | None = None
    installation_ids: list[UUID] = Field(default_factory=list)

    tenant_id: str | None = None
    integration_kind: str | None = None
    integration_connection_id: str | None = None

    enabled: bool | None = None
    configuration_state: str | None = None
    authentication_state: str | None = None
    verification_state: str | None = None

    failure_code: str | None = None
    installation_version: int | None = None

    discovered: int | None = None
    projected: int | None = None

    shop: CapabilityProviderInstallationEventShopRead | None = None

    created_at: datetime


class TaskVerificationCreateRequest(BaseModel):
    """
    Public task-verification request.

    user_id is intentionally absent. Ownership is derived exclusively from
    the authenticated user.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=500,
    )

    verification_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    capability_id: str = Field(
        min_length=1,
        max_length=255,
    )

    provider_id: str | None = Field(
        default=None,
        max_length=255,
    )

    provider_ref: str | None = Field(
        default=None,
        max_length=500,
    )

    action: str | None = Field(
        default=None,
        max_length=100,
    )

    tenant_id: str | None = Field(
        default=None,
        max_length=255,
    )

    correlation_id: str | None = Field(
        default=None,
        max_length=255,
    )

    workflow_run_id: str | None = Field(
        default=None,
        max_length=255,
    )

    task_id: str | None = Field(
        default=None,
        max_length=255,
    )

    inputs: dict = Field(
        default_factory=dict,
    )

    expected_outcome: dict = Field(
        default_factory=dict,
    )

    execution_output: object | None = None

    metadata: dict = Field(
        default_factory=dict,
    )


class TaskVerificationRetryRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=500,
    )


class TaskVerificationEvidenceRead(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    kind: str
    source: str
    observed_at_ts: float
    data: dict


class TaskVerificationResultRead(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    verification_id: str
    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    outcome: str
    method: str

    reason_code: str
    summary: str
    confidence: float
    retryable: bool

    observed_outcome: dict
    evidence: list[TaskVerificationEvidenceRead]

    completed_at_ts: float


class TaskVerificationExecutionRead(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    record_id: UUID
    attempt_number: int
    created: bool
    result: TaskVerificationResultRead


class TaskVerificationRecordRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    verification_id: str
    idempotency_key: str

    user_id: UUID
    tenant_id: str | None = None

    capability_id: str
    provider_id: str | None = None
    provider_ref: str | None = None
    action: str | None = None

    correlation_id: str | None = None
    workflow_run_id: str | None = None
    task_id: str | None = None

    attempt_number: int

    outcome: str
    method: str
    reason_code: str
    summary: str
    confidence: float
    retryable: bool

    inputs_json: dict
    requested_outcome_json: dict
    execution_output_json: object | None = None
    observed_outcome_json: dict
    evidence_json: list[dict]
    request_metadata_json: dict

    requested_at: datetime
    completed_at: datetime
    created_at: datetime


# ============================================================
# API composition helpers
# ============================================================


def build_provider_verifier_registry(
    *,
    db: AsyncSession,
) -> ProviderInstallationVerifierRegistry:
    """
    Compose provider installation verifiers available to the API.

    Provider implementations register here; runtime remains
    provider-agnostic.
    """

    registry = ProviderInstallationVerifierRegistry()

    register_shopify_provider_verifier(
        registry,
        db=db,
    )

    return registry


# ============================================================
# Capability API
# ============================================================

router = APIRouter(
    prefix="/capabilities",
    tags=["Capabilities"],
)


# ------------------------------------------------------------
# Performance
# ------------------------------------------------------------


@router.get(
    "/performance/summary",
    response_model=list[CapabilityProviderReliabilityReport],
)
async def summarize_capability_performance(
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    window_hours: int = Query(
        default=24,
        ge=1,
        le=8760,
    ),
    minimum_attempts: int = Query(
        default=10,
        ge=1,
        le=100000,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = CapabilityReliabilityService(
        db,
        policy=CapabilityReliabilityPolicy(
            minimum_attempts=minimum_attempts,
        ),
    )

    return await service.summarize(
        user_id=current_user.id,
        window_hours=window_hours,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        tenant_id=tenant_id,
    )


@router.get("/performance/observations")
async def list_capability_performance_observations(
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    failure_kind: str | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    window_hours: int = Query(
        default=24,
        ge=1,
        le=8760,
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
):
    (
        window_start,
        window_end,
        rows,
    ) = await CapabilityPerformanceQueryRepository(db).list_observations(
        user_id=current_user.id,
        window_hours=window_hours,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        tenant_id=tenant_id,
        failure_kind=failure_kind,
        correlation_id=correlation_id,
        limit=limit,
        offset=offset,
    )

    return {
        "window_start": window_start,
        "window_end": window_end,
        "limit": limit,
        "offset": offset,
        "items": [
            CapabilityPerformanceObservationRead.model_validate(row).model_dump(
                mode="json"
            )
            for row in rows
        ],
    }


# ------------------------------------------------------------
# Runtime policy
# ------------------------------------------------------------


@router.get(
    "/runtime-policy/effective",
    response_model=CapabilityRuntimePolicyEffectiveRead,
)
async def get_effective_capability_runtime_policy(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    snapshot = await DatabaseCapabilityRuntimePolicyReader(db).resolve_policy(
        user_id=str(current_user.id),
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
    )

    return CapabilityRuntimePolicyEffectiveRead(**snapshot.model_dump(mode="python"))


@router.get("/runtime-policy/revisions")
async def list_capability_runtime_policy_revisions(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = await CapabilityRuntimePolicyRepository(db).list_revisions(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [
            CapabilityRuntimePolicyRevisionRead.model_validate(row).model_dump(
                mode="json"
            )
            for row in rows
        ],
    }


@router.post(
    "/runtime-policy/revisions",
    response_model=CapabilityRuntimePolicyRevisionRead,
    status_code=201,
)
async def create_capability_runtime_policy_revision(
    request: CapabilityRuntimePolicyRevisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        scope = CapabilityRuntimePolicyScope(
            user_id=current_user.id,
            tenant_id=request.tenant_id,
            capability_id=request.capability_id,
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
        )

        repository = CapabilityRuntimePolicyRepository(db)
        row = await CapabilityRuntimePolicyOperations(
            db,
            repository=repository,
        ).append_revision(
            scope=scope,
            policy_payload=request.policy_payload,
            enabled=request.enabled,
            reason=request.reason,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return CapabilityRuntimePolicyRevisionRead.model_validate(row)


# ------------------------------------------------------------
# Provider health
# ------------------------------------------------------------


@router.get("/health/states")
async def list_capability_provider_health_states(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = await CapabilityProviderHealthControlService(db).list_states(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [
            CapabilityProviderHealthStateRead.model_validate(row).model_dump(
                mode="json"
            )
            for row in rows
        ],
    }


@router.get("/health/decisions")
async def list_capability_provider_health_decisions(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = await CapabilityProviderHealthRepository(db).list_decisions(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [
            CapabilityProviderHealthDecisionRead.model_validate(row).model_dump(
                mode="json"
            )
            for row in rows
        ],
    }


@router.patch("/health/override")
async def set_capability_provider_health_override(
    request: CapabilityProviderHealthOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        row = await CapabilityProviderHealthControlService(db).set_override(
            user_id=current_user.id,
            tenant_id=request.tenant_id,
            capability_id=request.capability_id,
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
            override_state=ProviderHealthState(request.override_state),
            reason=request.reason,
            override_until=request.override_until,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return CapabilityProviderHealthStateRead.model_validate(row).model_dump(mode="json")


@router.delete("/health/override")
async def clear_capability_provider_health_override(
    capability_id: str = Query(min_length=1),
    provider_id: str = Query(min_length=1),
    tenant_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    row = await CapabilityProviderHealthControlService(db).clear_override(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Provider health state not found",
        )

    return CapabilityProviderHealthStateRead.model_validate(row).model_dump(mode="json")


# ------------------------------------------------------------
# Provider installations
# ------------------------------------------------------------


@router.get(
    "/provider-installations",
)
async def list_provider_installations(
    tenant_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
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
    rows = await CapabilityProviderInstallationRepository(db).list_for_user(
        user_id=current_user.id,
        tenant_id=tenant_id,
        provider_id=provider_id,
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [
            CapabilityProviderInstallationRead.model_validate(row).model_dump(
                mode="json"
            )
            for row in rows
        ],
    }


@router.get(
    "/provider-installations/{provider_id}/events",
)
async def list_provider_installation_events(
    provider_id: str,
    tenant_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    outcome: str | None = Query(
        default=None,
        pattern=("^(connected|enabled|disabled|verified|failed|reconciled)$"),
    ),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
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
    try:
        rows = await ProviderInstallationHistoryQuery(db).list_events(
            user_id=current_user.id,
            provider_id=provider_id,
            tenant_id=tenant_id,
            event_type=event_type,
            outcome=outcome,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "provider_id": provider_id,
        "limit": limit,
        "offset": offset,
        "items": [
            CapabilityProviderInstallationEventRead(
                **sanitize_provider_installation_event(row)
            ).model_dump(mode="json")
            for row in rows
        ],
    }


@router.get(
    "/provider-installations/{provider_id}",
    response_model=(CapabilityProviderInstallationRead),
)
async def get_provider_installation(
    provider_id: str,
    tenant_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    row = await CapabilityProviderInstallationRepository(db).get_exact(
        user_id=current_user.id,
        tenant_id=tenant_id,
        provider_id=provider_id,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=("Provider installation not found"),
        )

    return CapabilityProviderInstallationRead.model_validate(row)


@router.patch(
    "/provider-installations/{provider_id}",
    response_model=(CapabilityProviderInstallationRead),
)
async def update_provider_installation_enabled(
    provider_id: str,
    request: (CapabilityProviderInstallationEnabledUpdate),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    repository = CapabilityProviderInstallationRepository(db)

    row = await CapabilityProviderInstallationOperations(
        db,
        repository=repository,
    ).set_enabled(
        user_id=current_user.id,
        tenant_id=request.tenant_id,
        provider_id=provider_id,
        enabled=request.enabled,
        lifecycle_events=ShopifyProviderLifecycleEvents(db),
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=("Provider installation not found"),
        )

    return CapabilityProviderInstallationRead.model_validate(row)


@router.post(
    "/provider-installations/{provider_id}/verify",
    response_model=(CapabilityProviderVerificationRead),
)
async def verify_provider_installation(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        result = await build_provider_verifier_registry(
            db=db,
        ).verify(
            provider_id,
            user_id=current_user.id,
        )
    except UnsupportedProviderVerificationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    row = await CapabilityProviderInstallationRepository(db).get_exact(
        user_id=current_user.id,
        tenant_id=None,
        provider_id=provider_id,
    )

    return CapabilityProviderVerificationRead(
        provider_id=provider_id,
        ok=bool(result.get("ok")),
        message=str(result.get("message") or ""),
        installation=(
            CapabilityProviderInstallationRead.model_validate(row)
            if row is not None
            else None
        ),
    )


@router.post(
    "/provider-installations/reconcile/shopify",
    response_model=(CapabilityProviderInstallationReconcileRead),
)
async def reconcile_shopify_provider_installation(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    connections = await ShopifyRepository(db).list_active_connections(
        user_id=current_user.id,
    )

    rows = await CapabilityProviderInstallationOperations(
        db,
    ).reconcile(
        user_id=current_user.id,
        connections=connections,
        projector=ShopifyProviderInstallationProjector(db),
        lifecycle_events=ShopifyProviderLifecycleEvents(db),
    )

    return CapabilityProviderInstallationReconcileRead(
        provider_id="shopify",
        discovered=len(connections),
        projected=len(rows),
        items=[CapabilityProviderInstallationRead.model_validate(row) for row in rows],
    )


# ------------------------------------------------------------
# Learning
# ------------------------------------------------------------


@router.post(
    "/learning-insight-candidates/generate",
    response_model=(CapabilityLearningCandidateGenerationResult),
    status_code=201,
)
async def generate_capability_learning_candidates(
    request: CapabilityLearningCandidateGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await CapabilityLearningInsightCandidateOperations(db).generate(
            user_id=current_user.id,
            request=request,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get(
    "/learning-insight-candidates",
    response_model=dict,
)
async def list_capability_learning_candidates(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    action: str | None = Query(default=None),
    status: (CapabilityLearningCandidateStatus | None) = Query(default=None),
    approval_status: (CapabilityLearningApprovalStatus | None) = Query(default=None),
    promotion_eligible: bool | None = Query(default=None),
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
    items = await CapabilityLearningInsightCandidateOperations(db).list_latest(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        action=action,
        status=(status.value if status is not None else None),
        approval_status=(
            approval_status.value if approval_status is not None else None
        ),
        promotion_eligible=(promotion_eligible),
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [item.model_dump(mode="json") for item in items],
    }


@router.get(
    "/learning-insight-candidates/{candidate_id}/history",
    response_model=list[CapabilityLearningInsightCandidate],
)
async def get_capability_learning_candidate_history(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = await CapabilityLearningInsightCandidateOperations(db).history(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if not items:
        raise HTTPException(
            status_code=404,
            detail=("Learning insight candidate not found"),
        )

    return items


@router.get(
    "/learning-insight-candidates/{candidate_id}",
    response_model=(CapabilityLearningInsightCandidate),
)
async def get_capability_learning_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    candidate = await CapabilityLearningInsightCandidateOperations(db).get_latest(
        user_id=current_user.id,
        candidate_id=candidate_id,
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=("Learning insight candidate not found"),
        )

    return candidate


@router.post(
    "/learning-insight-candidates/{candidate_id}/review",
    response_model=(CapabilityLearningInsightCandidate),
)
async def review_capability_learning_candidate(
    candidate_id: UUID,
    request: CapabilityLearningCandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        candidate = await CapabilityLearningInsightCandidateOperations(db).review(
            user_id=current_user.id,
            candidate_id=candidate_id,
            reviewed_by_user_id=(current_user.id),
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
            detail=("Learning insight candidate not found"),
        )

    return candidate


@router.post(
    "/learning-insight-candidates/{candidate_id}/promotions",
    response_model=(CapabilityLearningInsightPromotion),
    status_code=201,
)
async def promote_capability_learning_candidate(
    candidate_id: UUID,
    request: CapabilityLearningPromotionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        promotion = await CapabilityLearningInsightPromotionOperations(db).promote(
            user_id=current_user.id,
            candidate_id=candidate_id,
            created_by_user_id=(current_user.id),
            request=request,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    if promotion is None:
        raise HTTPException(
            status_code=404,
            detail=("Learning insight candidate not found"),
        )

    return promotion


@router.get(
    "/learning-insight-promotions",
    response_model=dict,
)
async def list_capability_learning_promotions(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    candidate_id: UUID | None = Query(default=None),
    status: (CapabilityLearningPromotionStatus | None) = Query(default=None),
    promotion_target: (CapabilityLearningPromotionTarget | None) = Query(default=None),
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
    items = await CapabilityLearningInsightPromotionOperations(db).list_latest(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        candidate_id=candidate_id,
        status=(status.value if status is not None else None),
        promotion_target=(
            promotion_target.value if promotion_target is not None else None
        ),
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [item.model_dump(mode="json") for item in items],
    }


@router.get(
    "/learning-insight-promotions/{promotion_id}/history",
    response_model=list[CapabilityLearningInsightPromotion],
)
async def get_capability_learning_promotion_history(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = await CapabilityLearningInsightPromotionOperations(db).history(
        user_id=current_user.id,
        promotion_id=promotion_id,
    )

    if not items:
        raise HTTPException(
            status_code=404,
            detail=("Learning insight promotion not found"),
        )

    return items


@router.get(
    "/learning-insight-promotions/{promotion_id}",
    response_model=(CapabilityLearningInsightPromotion),
)
async def get_capability_learning_promotion(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    promotion = await CapabilityLearningInsightPromotionOperations(db).get_latest(
        user_id=current_user.id,
        promotion_id=promotion_id,
    )

    if promotion is None:
        raise HTTPException(
            status_code=404,
            detail=("Learning insight promotion not found"),
        )

    return promotion


@router.post(
    "/learning-insight-promotions/{promotion_id}/revoke",
    response_model=(CapabilityLearningInsightPromotion),
)
async def revoke_capability_learning_promotion(
    promotion_id: UUID,
    request: CapabilityLearningPromotionRevokeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        promotion = await CapabilityLearningInsightPromotionOperations(db).revoke(
            user_id=current_user.id,
            promotion_id=promotion_id,
            created_by_user_id=(current_user.id),
            request=request,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    if promotion is None:
        raise HTTPException(
            status_code=404,
            detail=("Learning insight promotion not found"),
        )

    return promotion


@router.get(
    "/learning-observations/trends",
    response_model=list[CapabilityLearningTrendReport],
)
async def analyze_capability_learning_trends(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    action: str | None = Query(default=None),
    window_hours: int = Query(
        default=168,
        ge=1,
        le=4380,
    ),
    minimum_effective_sample_size: float = Query(
        default=5.0,
        gt=0.0,
        le=100000.0,
    ),
    meaningful_success_delta: float = Query(
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
    service = CapabilityLearningTrendService(
        db,
        aggregation_policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=(minimum_effective_sample_size)
            )
        ),
        trend_policy=(
            CapabilityLearningTrendPolicy(
                meaningful_success_delta=(meaningful_success_delta),
                contradiction_threshold=(contradiction_threshold),
            )
        ),
    )

    return await service.analyze(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        action=action,
        window_hours=window_hours,
    )


@router.get(
    "/learning-observations/summary",
    response_model=list[CapabilityLearningSummary],
)
async def summarize_capability_learning_observations(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    action: str | None = Query(default=None),
    window_hours: int = Query(
        default=720,
        ge=1,
        le=8760,
    ),
    minimum_effective_sample_size: float = Query(
        default=5.0,
        gt=0.0,
        le=100000.0,
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = CapabilityLearningSummaryService(
        db,
        policy=(
            CapabilityLearningAggregationPolicy(
                minimum_effective_sample_size=(minimum_effective_sample_size)
            )
        ),
    )

    return await service.summarize(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        action=action,
        window_hours=window_hours,
    )


@router.get(
    "/learning-observations",
)
async def list_capability_learning_observations(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    provider_ref: str | None = Query(default=None),
    action: str | None = Query(default=None),
    outcome: str | None = Query(
        default=None,
        pattern=("^(verified|partially_verified|failed|inconclusive|not_verifiable)$"),
    ),
    is_final: bool | None = Query(default=None),
    retryable: bool | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    workflow_run_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
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
    rows = await CapabilityLearningObservationRepository(db).list_for_user(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=provider_ref,
        action=action,
        outcome=outcome,
        is_final=is_final,
        retryable=retryable,
        correlation_id=correlation_id,
        workflow_run_id=workflow_run_id,
        task_id=task_id,
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [
            CapabilityLearningObservationRead.model_validate(row).model_dump(
                mode="json"
            )
            for row in rows
        ],
    }


@router.get(
    "/learning-observations/record/{record_id}",
    response_model=(CapabilityLearningObservationRead),
)
async def get_capability_learning_observation(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    row = await CapabilityLearningObservationRepository(db).get_for_user(
        user_id=current_user.id,
        record_id=record_id,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=("Capability learning observation not found"),
        )

    return CapabilityLearningObservationRead.model_validate(row)


# ------------------------------------------------------------
# Task verification
# ------------------------------------------------------------


@router.post(
    "/task-verifications",
    response_model=TaskVerificationExecutionRead,
    status_code=201,
)
async def create_task_verification(
    request: TaskVerificationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    runtime_services = build_application_runtime_services(
        db=db,
        user_id=current_user.id,
        tenant_id=request.tenant_id,
    )

    verification_request = TaskVerificationRequest(
        **request.model_dump(
            exclude={
                "idempotency_key",
                "verification_id",
            },
            mode="python",
        ),
        **(
            {"verification_id": (request.verification_id)}
            if request.verification_id is not None
            else {}
        ),
        user_id=str(current_user.id),
    )

    try:
        execution = await runtime_services.task_verification.verify(
            user_id=current_user.id,
            request=verification_request,
            idempotency_key=(request.idempotency_key),
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return TaskVerificationExecutionRead(**execution.model_dump(mode="python"))


@router.get(
    "/task-verifications",
)
async def list_task_verifications(
    tenant_id: str | None = Query(default=None),
    capability_id: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    outcome: str | None = Query(
        default=None,
        pattern=("^(verified|partially_verified|failed|inconclusive|not_verifiable)$"),
    ),
    correlation_id: str | None = Query(default=None),
    workflow_run_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    retryable: bool | None = Query(default=None),
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
    rows = await TaskVerificationRepository(db).list_for_user(
        user_id=current_user.id,
        tenant_id=tenant_id,
        capability_id=capability_id,
        provider_id=provider_id,
        action=action,
        outcome=outcome,
        correlation_id=correlation_id,
        workflow_run_id=(workflow_run_id),
        task_id=task_id,
        retryable=retryable,
        limit=limit,
        offset=offset,
    )

    return {
        "limit": limit,
        "offset": offset,
        "items": [
            TaskVerificationRecordRead.model_validate(row).model_dump(mode="json")
            for row in rows
        ],
    }


@router.get(
    "/task-verifications/record/{record_id}",
    response_model=TaskVerificationRecordRead,
)
async def get_task_verification_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    row = await TaskVerificationRepository(db).get(
        user_id=current_user.id,
        record_id=record_id,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=("Task verification record not found"),
        )

    return TaskVerificationRecordRead.model_validate(row)


@router.get(
    "/task-verifications/{verification_id}/attempts",
)
async def list_task_verification_attempts(
    verification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = await TaskVerificationRepository(db).list_attempts(
        user_id=current_user.id,
        verification_id=verification_id,
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=("Task verification not found"),
        )

    return {
        "verification_id": verification_id,
        "items": [
            TaskVerificationRecordRead.model_validate(row).model_dump(mode="json")
            for row in rows
        ],
    }


@router.post(
    "/task-verifications/{verification_id}/retry",
    response_model=TaskVerificationExecutionRead,
    status_code=201,
)
async def retry_task_verification(
    verification_id: str,
    request: TaskVerificationRetryRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    repository = TaskVerificationRepository(db)

    attempts = await repository.list_attempts(
        user_id=current_user.id,
        verification_id=verification_id,
    )

    if not attempts:
        raise HTTPException(
            status_code=404,
            detail=("Task verification not found"),
        )

    latest = attempts[-1]

    if not latest.retryable:
        raise HTTPException(
            status_code=409,
            detail=("Latest task verification attempt is not retryable"),
        )

    verification_request = TaskVerificationRequest(
        verification_id=(latest.verification_id),
        capability_id=(latest.capability_id),
        provider_id=(latest.provider_id),
        provider_ref=(latest.provider_ref),
        action=latest.action,
        user_id=str(current_user.id),
        tenant_id=latest.tenant_id,
        correlation_id=(latest.correlation_id),
        workflow_run_id=(latest.workflow_run_id),
        task_id=latest.task_id,
        inputs=dict(latest.inputs_json or {}),
        expected_outcome=dict(latest.requested_outcome_json or {}),
        execution_output=(latest.execution_output_json),
        metadata=dict(latest.request_metadata_json or {}),
    )

    runtime_services = build_application_runtime_services(
        db=db,
        user_id=current_user.id,
        tenant_id=latest.tenant_id,
    )

    try:
        execution = await runtime_services.task_verification.verify(
            user_id=current_user.id,
            request=verification_request,
            idempotency_key=(request.idempotency_key),
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return TaskVerificationExecutionRead(**execution.model_dump(mode="python"))


# ------------------------------------------------------------
# Catalog and matching
# ------------------------------------------------------------


@router.get("")
async def list_capabilities(
    q: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
):
    registry = build_capability_registry()
    items = registry.discover(
        query=q,
        domain=domain,
        category=category,
        limit=limit,
    )
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/tenant")
async def list_tenant_capabilities(
    tenant_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    registry = await build_capability_registry_for_tenant(db=db, tenant_id=tenant_id)
    items = registry.discover(
        query=q,
        domain=domain,
        category=category,
        limit=limit,
    )
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/{capability_id}")
async def get_capability(capability_id: str):
    registry = build_capability_registry()
    return registry.get(capability_id).model_dump(mode="json")


@router.post("/match")
async def match_capability_candidates(request: CapabilityMatchRequest):
    response = match_capabilities(request)
    return response.model_dump(mode="json")


@router.post(
    "/match/advisory-aware",
    response_model=(CapabilityAdvisoryMatchResponse),
)
async def match_capability_candidates_with_advisories(
    request: CapabilityAdvisoryMatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await CapabilityPlannerAdvisoryComposer(db).compose(
            user_id=current_user.id,
            request=request,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get("/metadata/overrides")
async def list_capability_metadata_overrides(
    tenant_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    repo = CapabilityMetadataRepository(db)
    rows = await repo.list_for_tenant(tenant_id=tenant_id)
    return {
        "items": [
            CapabilityMetadataRead.model_validate(row).model_dump(mode="json")
            for row in rows
        ]
    }


@router.put("/metadata/overrides")
async def upsert_capability_metadata_override(
    request: CapabilityMetadataUpsert,
    db: AsyncSession = Depends(get_db),
):
    repo = CapabilityMetadataRepository(db)
    row = await repo.upsert(
        capability_id=request.capability_id,
        tenant_id=request.tenant_id,
        display_name=request.display_name,
        description=request.description,
        domain=request.domain,
        category=request.category,
        status=request.status,
        tags=request.tags,
        extra=request.extra,
        is_enabled=request.is_enabled,
    )
    return CapabilityMetadataRead.model_validate(row).model_dump(mode="json")


@router.delete("/metadata/overrides/{capability_id}")
async def delete_capability_metadata_override(
    capability_id: str,
    tenant_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    repo = CapabilityMetadataRepository(db)
    deleted = await repo.delete(capability_id=capability_id, tenant_id=tenant_id)
    return {"deleted": deleted}


__all__ = ["router"]
