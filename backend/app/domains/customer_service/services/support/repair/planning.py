from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.support.repair.planner import (
    CUSTOMER_SUPPORT_REPAIR_POLICY_VERSION,
)
from app.domains.customer_service.services.support.repair.registry import (
    register_customer_support_repair_planners,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan_loader import (
    CustomerSupportReviewPlanLoader,
    LoadedCustomerSupportReviewPlan,
)
from app.platform.events.event_store import PlatformEventStore
from app.runtime.objectives.repair import (
    OBJECTIVE_REPAIR_EXECUTION_TERMINAL_STATUSES,
    ObjectiveRepairConstraints,
    ObjectiveRepairDisposition,
    ObjectiveRepairExecutionRepository,
    ObjectiveRepairExecutionService,
    ObjectiveRepairExecutionWrite,
    ObjectiveRepairPlan,
    ObjectiveRepairPlannerRegistry,
    ObjectiveRepairPlanningContext,
    ObjectiveRepairRequest,
    ObjectiveRepairRequestBuilder,
)
from app.runtime.objectives.resolution import (
    ObjectiveResolutionRepository,
)
from app.tcos.cognitive import (
    ObjectiveRepairDelegationDecision,
    ObjectiveRepairDelegationKind,
)


OBJECTIVE_REPAIR_PLANNING_REQUESTED_EVENT = (
    "runtime.objective.repair.planning.requested"
)

OBJECTIVE_REPAIR_PLANNING_EVENT_SOURCE = (
    "runtime.objective_repair_planning"
)

CUSTOMER_SUPPORT_REPAIR_PLANNER_REF = (
    "customer_support_objective_repair"
)

CUSTOMER_SUPPORT_REPAIR_ALLOWED_DISPOSITIONS = (
    ObjectiveRepairDisposition.RETRY_OPERATION,
    ObjectiveRepairDisposition.WAIT_FOR_RESULT,
    ObjectiveRepairDisposition.REPLAN_REMAINING,
    ObjectiveRepairDisposition.REQUEST_HUMAN_ACTION,
    ObjectiveRepairDisposition.STOP_REPAIR,
)


class CustomerSupportRepairPlanningError(RuntimeError):
    """Base failure for product repair-planning coordination."""


class CustomerSupportRepairPlanningNotFoundError(
    CustomerSupportRepairPlanningError
):
    """The delegated durable source was not found for the user."""


class CustomerSupportRepairPlanningIdentityError(
    CustomerSupportRepairPlanningError
):
    """Delegation identity does not match durable objective truth."""


class CustomerSupportRepairPlanningAttemptError(
    CustomerSupportRepairPlanningError
):
    """Delegation attempt does not match durable repair history."""


@dataclass(frozen=True)
class CustomerSupportRepairPlanningResult:
    command_event_id: UUID
    write: ObjectiveRepairExecutionWrite

    request: ObjectiveRepairRequest
    plan: ObjectiveRepairPlan

    requested_attempt_number: int
    canonical_review_plan: LoadedCustomerSupportReviewPlan


class CustomerSupportRepairPlanningCoordinator:
    """
    Convert a typed cognitive repair delegation into one durable
    customer-support repair plan.

    This coordinator owns product planning orchestration only. It
    does not build, enqueue, launch, or execute a repair workflow.

    The existing objective-repair planned event remains the sole
    downstream workflow-launch trigger.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        resolutions: ObjectiveResolutionRepository | None = None,
        repairs: ObjectiveRepairExecutionRepository | None = None,
        review_plans: CustomerSupportReviewPlanLoader | None = None,
        registry: ObjectiveRepairPlannerRegistry | None = None,
        request_builder: ObjectiveRepairRequestBuilder | None = None,
        repair_service: ObjectiveRepairExecutionService | None = None,
        events: PlatformEventStore | None = None,
    ) -> None:
        self.db = db

        self.resolutions = (
            resolutions or ObjectiveResolutionRepository(db)
        )
        self.repairs = (
            repairs or ObjectiveRepairExecutionRepository(db)
        )
        self.review_plans = (
            review_plans or CustomerSupportReviewPlanLoader(db)
        )

        self.registry = registry or self._build_registry()
        self.request_builder = (
            request_builder or ObjectiveRepairRequestBuilder()
        )
        self.repair_service = (
            repair_service
            or ObjectiveRepairExecutionService(
                db,
                repository=self.repairs,
            )
        )
        self.events = events or PlatformEventStore(db)

    async def plan(
        self,
        *,
        decision: ObjectiveRepairDelegationDecision,
        user_id: UUID,
        tenant_id: str | None,
        commit: bool = True,
    ) -> CustomerSupportRepairPlanningResult:
        self._validate_requested_decision(decision)

        resolution_record_id = self._required_resolution_id(
            decision
        )
        requested_attempt_number = (
            self._required_requested_attempt(decision)
        )
        normalized_tenant_id = self._normalize_tenant_id(
            tenant_id
        )

        resolution = await self.resolutions.get_for_user(
            user_id=user_id,
            record_id=resolution_record_id,
        )

        if resolution is None:
            raise CustomerSupportRepairPlanningNotFoundError(
                "Objective resolution record was not found "
                "for user"
            )

        self._validate_resolution_identity(
            decision=decision,
            resolution=resolution,
            tenant_id=normalized_tenant_id,
        )

        assessment = self.resolutions.assessment_from_record(
            resolution
        )

        canonical = await self.review_plans.load_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        self._validate_canonical_resolution(
            canonical=canonical,
            resolution_record_id=resolution_record_id,
        )

        latest = await self.repairs.get_latest_for_resolution(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        self._validate_attempt(
            decision=decision,
            latest=latest,
            requested_attempt_number=(
                requested_attempt_number
            ),
        )

        prior_plans = self._prior_plans(latest)

        constraints = self._constraints(
            requested_attempt_number=(
                requested_attempt_number
            ),
            canonical=canonical,
        )

        request = self.request_builder.build(
            resolution_record_ref=str(resolution.id),
            resolution_projection_version=(
                resolution.projection_version
            ),
            assessment=assessment,
            constraints=constraints,
            context={
                "tenant_id": normalized_tenant_id,
                "delegation_kind": decision.kind.value,
                "delegation_reason_code": (
                    decision.reason_code
                ),
                "delegation_schema_version": (
                    decision.schema_version
                ),
                "requested_attempt_number": (
                    requested_attempt_number
                ),
                "review_plan_id": canonical.review_plan_id,
                "support_outcome_id": str(
                    canonical.support_outcome_id
                ),
                "workflow_run_id": str(
                    canonical.workflow_run_id
                ),
            },
        )

        planner = self.registry.resolve(
            namespace=resolution.objective_namespace,
            objective_type=resolution.objective_type,
        )

        planning_context = ObjectiveRepairPlanningContext(
            request=request,
            resolution=assessment,
            prior_repair_plans=prior_plans,
            product_context={
                "review_plan_id": canonical.review_plan_id,
                "review_plan": (
                    canonical.review_plan.model_dump(
                        mode="json"
                    )
                ),
                "support_outcome_id": str(
                    canonical.support_outcome_id
                ),
                "workflow_run_id": str(
                    canonical.workflow_run_id
                ),
                "resolution_record_id": str(
                    resolution_record_id
                ),
            },
        )

        plan = planner.plan_repair(planning_context)

        try:
            command_event = await self.events.append(
                event_type=(
                    OBJECTIVE_REPAIR_PLANNING_REQUESTED_EVENT
                ),
                source=(
                    OBJECTIVE_REPAIR_PLANNING_EVENT_SOURCE
                ),
                user_id=user_id,
                payload={
                    "resolution_record_id": str(
                        resolution_record_id
                    ),
                    "objective_namespace": (
                        resolution.objective_namespace
                    ),
                    "objective_type": (
                        resolution.objective_type
                    ),
                    "objective_ref": resolution.objective_ref,
                    "objective_version": (
                        resolution.objective_version
                    ),
                    "delegation_kind": (
                        decision.kind.value
                    ),
                    "requested_attempt_number": (
                        requested_attempt_number
                    ),
                },
                meta={
                    "tenant_id": normalized_tenant_id,
                    "delegation_schema_version": (
                        decision.schema_version
                    ),
                    "delegation_reason_code": (
                        decision.reason_code
                    ),
                    "planner_ref": (
                        CUSTOMER_SUPPORT_REPAIR_PLANNER_REF
                    ),
                    "planner_policy_version": (
                        CUSTOMER_SUPPORT_REPAIR_POLICY_VERSION
                    ),
                },
                commit=False,
            )

            write = await self.repair_service.record_plan(
                source_event_id=command_event.id,
                user_id=user_id,
                tenant_id=normalized_tenant_id,
                resolution_record_id=(
                    resolution_record_id
                ),
                request=request,
                plan=plan,
                planner_ref=(
                    CUSTOMER_SUPPORT_REPAIR_PLANNER_REF
                ),
                planner_policy_version=(
                    CUSTOMER_SUPPORT_REPAIR_POLICY_VERSION
                ),
                attempt_number=(
                    requested_attempt_number
                ),
                commit=False,
            )

            if commit:
                await self.db.commit()
                await self.db.refresh(write.record)
            else:
                await self.db.flush()

        except Exception:
            await self.db.rollback()
            raise

        return CustomerSupportRepairPlanningResult(
            command_event_id=command_event.id,
            write=write,
            request=request,
            plan=plan,
            requested_attempt_number=(
                requested_attempt_number
            ),
            canonical_review_plan=canonical,
        )

    @staticmethod
    def _build_registry() -> ObjectiveRepairPlannerRegistry:
        registry = ObjectiveRepairPlannerRegistry()

        register_customer_support_repair_planners(
            registry
        )

        return registry

    @staticmethod
    def _validate_requested_decision(
        decision: ObjectiveRepairDelegationDecision,
    ) -> None:
        planning_kinds = {
            (
                ObjectiveRepairDelegationKind
                .REPAIR_PLANNING_REQUESTED
            ),
            (
                ObjectiveRepairDelegationKind
                .SUBSEQUENT_REPAIR_PLANNING_REQUESTED
            ),
        }

        if decision.kind not in planning_kinds:
            raise CustomerSupportRepairPlanningIdentityError(
                "Repair planning requires a planning-request "
                "delegation"
            )

        if not decision.requested:
            raise CustomerSupportRepairPlanningIdentityError(
                "Repair planning delegation is not requested"
            )

        if not decision.safety.product_planning_required:
            raise CustomerSupportRepairPlanningIdentityError(
                "Delegation does not require product planning"
            )

        forbidden = (
            decision.safety.persists_repair,
            decision.safety.publishes_event,
            decision.safety.enqueues_job,
            decision.safety.launches_workflow,
            decision.safety.authorizes_execution,
            decision.safety.bypasses_product_registry,
            (
                decision.safety
                .bypasses_canonical_source_loading
            ),
            decision.safety.bypasses_idempotency,
            decision.safety.bypasses_approval,
            decision.safety.bypasses_verification,
        )

        if any(forbidden):
            raise CustomerSupportRepairPlanningIdentityError(
                "Delegation violates repair-planning safety "
                "boundaries"
            )

    @staticmethod
    def _required_resolution_id(
        decision: ObjectiveRepairDelegationDecision,
    ) -> UUID:
        if decision.resolution_record_id is None:
            raise CustomerSupportRepairPlanningIdentityError(
                "Repair planning delegation requires "
                "resolution_record_id"
            )

        return decision.resolution_record_id

    @staticmethod
    def _required_requested_attempt(
        decision: ObjectiveRepairDelegationDecision,
    ) -> int:
        value = decision.requested_attempt_number

        if value is None or value < 1:
            raise CustomerSupportRepairPlanningAttemptError(
                "Repair planning delegation requires a valid "
                "requested attempt number"
            )

        return value

    @classmethod
    def _validate_resolution_identity(
        cls,
        *,
        decision: ObjectiveRepairDelegationDecision,
        resolution: Any,
        tenant_id: str | None,
    ) -> None:
        expected = {
            "objective_namespace": (
                decision.objective_namespace
            ),
            "objective_type": decision.objective_type,
            "objective_ref": decision.objective_ref,
            "objective_version": (
                decision.objective_version
            ),
        }

        mismatches = [
            name
            for name, value in expected.items()
            if value != getattr(resolution, name)
        ]

        if mismatches:
            raise CustomerSupportRepairPlanningIdentityError(
                "Delegation objective identity does not match "
                "durable resolution: "
                + ", ".join(mismatches)
            )

        resolution_tenant = cls._normalize_tenant_id(
            resolution.tenant_id
        )

        if resolution_tenant != tenant_id:
            raise CustomerSupportRepairPlanningIdentityError(
                "Delegation tenant does not match durable "
                "resolution"
            )

    @staticmethod
    def _validate_canonical_resolution(
        *,
        canonical: LoadedCustomerSupportReviewPlan,
        resolution_record_id: UUID,
    ) -> None:
        if (
            canonical.resolution_record_id
            != resolution_record_id
        ):
            raise CustomerSupportRepairPlanningIdentityError(
                "Canonical review plan does not match the "
                "delegated resolution"
            )

    @staticmethod
    def _validate_attempt(
        *,
        decision: ObjectiveRepairDelegationDecision,
        latest: Any | None,
        requested_attempt_number: int,
    ) -> None:
        if latest is None:
            if requested_attempt_number != 1:
                raise CustomerSupportRepairPlanningAttemptError(
                    "First durable repair attempt must be 1"
                )

            if (
                decision.kind
                != ObjectiveRepairDelegationKind
                .REPAIR_PLANNING_REQUESTED
            ):
                raise CustomerSupportRepairPlanningAttemptError(
                    "Subsequent repair planning requires a "
                    "prior durable repair"
                )

            return

        latest_attempt = int(latest.attempt_number)

        if requested_attempt_number < latest_attempt:
            raise CustomerSupportRepairPlanningAttemptError(
                "Requested repair attempt is stale"
            )

        if requested_attempt_number > latest_attempt + 1:
            raise CustomerSupportRepairPlanningAttemptError(
                "Requested repair attempt skips durable "
                "repair history"
            )

        if requested_attempt_number == latest_attempt:
            # Same-attempt retry. Persistence must converge on
            # the existing semantic repair identity.
            return

        if (
            decision.kind
            != ObjectiveRepairDelegationKind
            .SUBSEQUENT_REPAIR_PLANNING_REQUESTED
        ):
            raise CustomerSupportRepairPlanningAttemptError(
                "New repair attempt requires a subsequent "
                "planning delegation"
            )

        if decision.current_attempt_number != latest_attempt:
            raise CustomerSupportRepairPlanningAttemptError(
                "Delegation current attempt does not match "
                "durable repair history"
            )

        if decision.repair_execution_id != latest.id:
            raise CustomerSupportRepairPlanningAttemptError(
                "Delegation repair execution does not match "
                "the latest durable repair"
            )

        if (
            latest.status
            not in OBJECTIVE_REPAIR_EXECUTION_TERMINAL_STATUSES
        ):
            raise CustomerSupportRepairPlanningAttemptError(
                "Subsequent planning requires a terminal "
                "prior repair attempt"
            )

    @staticmethod
    def _prior_plans(
        latest: Any | None,
    ) -> tuple[ObjectiveRepairPlan, ...]:
        if latest is None:
            return ()

        return (
            ObjectiveRepairPlan.model_validate(
                dict(latest.plan_json or {})
            ),
        )

    @staticmethod
    def _constraints(
        *,
        requested_attempt_number: int,
        canonical: LoadedCustomerSupportReviewPlan,
    ) -> ObjectiveRepairConstraints:
        return ObjectiveRepairConstraints(
            allow_automatic_execution=False,
            require_human_approval=False,
            allowed_dispositions=(
                CUSTOMER_SUPPORT_REPAIR_ALLOWED_DISPOSITIONS
            ),
            maximum_target_count=len(
                canonical.review_plan.operations
            ),
            metadata={
                "policy": (
                    "customer_support_objective_repair"
                ),
                "policy_version": (
                    CUSTOMER_SUPPORT_REPAIR_POLICY_VERSION
                ),
                "requested_attempt_number": (
                    requested_attempt_number
                ),
                "fresh_approval_required_for_mutation": True,
                "automatic_mutation_allowed": False,
            },
        )

    @staticmethod
    def _normalize_tenant_id(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()

        return normalized or None


__all__ = [
    "CUSTOMER_SUPPORT_REPAIR_ALLOWED_DISPOSITIONS",
    "CUSTOMER_SUPPORT_REPAIR_PLANNER_REF",
    "OBJECTIVE_REPAIR_PLANNING_EVENT_SOURCE",
    "OBJECTIVE_REPAIR_PLANNING_REQUESTED_EVENT",
    "CustomerSupportRepairPlanningAttemptError",
    "CustomerSupportRepairPlanningCoordinator",
    "CustomerSupportRepairPlanningError",
    "CustomerSupportRepairPlanningIdentityError",
    "CustomerSupportRepairPlanningNotFoundError",
    "CustomerSupportRepairPlanningResult",
]
