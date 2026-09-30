from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.repositories.customer_support_outcomes import (
    CustomerSupportOutcomeRepository,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewPlan,
)
from app.models.models import ObjectiveResolutionRecord
from app.runtime.persistence import (
    RunStore,
    build_run_store,
)


class CustomerSupportReviewPlanNotFoundError(
    LookupError
):
    pass


class CustomerSupportReviewPlanLineageError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class LoadedCustomerSupportReviewPlan:
    review_plan_id: str
    review_plan: SupportReviewPlan
    support_outcome_id: UUID
    workflow_run_id: UUID
    resolution_record_id: UUID | None = None


class CustomerSupportReviewPlanLoader:
    """
    Recover the immutable canonical support review plan from the
    original durable workflow definition.

    The loader does not reconstruct plan facts from outcome
    operations. The original workflow metadata is the source of
    truth because it retains provider order identity, operation
    references, item scope, and replacement address.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        outcomes: (
            CustomerSupportOutcomeRepository | None
        ) = None,
        run_store: RunStore | None = None,
    ) -> None:
        self.db = db
        self.outcomes = (
            outcomes
            or CustomerSupportOutcomeRepository(db)
        )
        self.run_store = (
            run_store or build_run_store(db)
        )

    async def load_for_resolution(
        self,
        *,
        user_id: UUID,
        resolution_record_id: UUID,
    ) -> LoadedCustomerSupportReviewPlan:
        resolution = await self._resolution_for_user(
            user_id=user_id,
            resolution_record_id=resolution_record_id,
        )

        if resolution is None:
            raise CustomerSupportReviewPlanNotFoundError(
                "Objective resolution record was not found "
                "for user"
            )

        support_outcome_id = self._uuid(
            resolution.source_outcome_ref,
            "resolution source_outcome_ref",
        )

        loaded = await self.load_for_outcome(
            user_id=user_id,
            support_outcome_id=support_outcome_id,
        )

        if (
            resolution.workflow_run_id is not None
            and str(loaded.workflow_run_id)
            != str(resolution.workflow_run_id).strip()
        ):
            raise CustomerSupportReviewPlanLineageError(
                "Objective resolution workflow run does not "
                "match the canonical support outcome"
            )

        if (
            resolution.objective_ref.strip()
            != loaded.review_plan_id
        ):
            raise CustomerSupportReviewPlanLineageError(
                "Objective resolution reference does not "
                "match the canonical review plan"
            )

        return LoadedCustomerSupportReviewPlan(
            review_plan_id=loaded.review_plan_id,
            review_plan=loaded.review_plan,
            support_outcome_id=(
                loaded.support_outcome_id
            ),
            workflow_run_id=loaded.workflow_run_id,
            resolution_record_id=resolution.id,
        )

    async def load_for_outcome(
        self,
        *,
        user_id: UUID,
        support_outcome_id: UUID,
    ) -> LoadedCustomerSupportReviewPlan:
        outcome = await self.outcomes.get_for_user(
            user_id=user_id,
            outcome_id=support_outcome_id,
        )

        if outcome is None:
            raise CustomerSupportReviewPlanNotFoundError(
                "Customer-support outcome was not found "
                "for user"
            )

        run = await self.run_store.load_run(
            run_id=outcome.workflow_run_id
        )

        if run is None:
            raise CustomerSupportReviewPlanNotFoundError(
                "Original customer-support workflow run "
                "was not found"
            )

        self._require_run_owner(
            run=run,
            user_id=user_id,
        )

        review_plan_id, review_plan = (
            self._review_plan_from_workflow(
                workflow=run.get("workflow"),
            )
        )

        self._require_outcome_lineage(
            outcome=outcome,
            review_plan_id=review_plan_id,
            review_plan=review_plan,
            run=run,
        )

        return LoadedCustomerSupportReviewPlan(
            review_plan_id=review_plan_id,
            review_plan=review_plan,
            support_outcome_id=outcome.id,
            workflow_run_id=outcome.workflow_run_id,
        )

    async def _resolution_for_user(
        self,
        *,
        user_id: UUID,
        resolution_record_id: UUID,
    ) -> ObjectiveResolutionRecord | None:
        result = await self.db.execute(
            select(ObjectiveResolutionRecord).where(
                ObjectiveResolutionRecord.id
                == resolution_record_id,
                ObjectiveResolutionRecord.user_id
                == user_id,
            )
        )

        return result.scalar_one_or_none()

    @classmethod
    def _review_plan_from_workflow(
        cls,
        *,
        workflow: Any,
    ) -> tuple[str, SupportReviewPlan]:
        if not isinstance(workflow, dict):
            raise CustomerSupportReviewPlanLineageError(
                "Original workflow definition is missing"
            )

        metadata = workflow.get("metadata")

        if not isinstance(metadata, dict):
            raise CustomerSupportReviewPlanLineageError(
                "Original workflow metadata is missing"
            )

        if metadata.get("kind") != (
            "customer_support_review"
        ):
            raise CustomerSupportReviewPlanLineageError(
                "Original workflow is not a canonical "
                "customer-support review workflow"
            )

        support_review = metadata.get(
            "support_review"
        )

        if not isinstance(support_review, dict):
            raise CustomerSupportReviewPlanLineageError(
                "Original workflow support_review metadata "
                "is missing"
            )

        metadata_plan_id = cls._required_text(
            metadata.get("review_plan_id"),
            "workflow metadata review_plan_id",
        )
        context_plan_id = cls._required_text(
            support_review.get("review_plan_id"),
            "support_review review_plan_id",
        )

        if metadata_plan_id != context_plan_id:
            raise CustomerSupportReviewPlanLineageError(
                "Workflow review-plan identities conflict"
            )

        raw_plan = support_review.get(
            "review_plan"
        )

        if not isinstance(raw_plan, dict):
            raise CustomerSupportReviewPlanLineageError(
                "Canonical support review plan payload "
                "is missing"
            )

        try:
            review_plan = (
                SupportReviewPlan.model_validate(
                    raw_plan
                )
            )
        except ValidationError as exc:
            raise CustomerSupportReviewPlanLineageError(
                "Canonical support review plan payload "
                "is invalid"
            ) from exc

        return metadata_plan_id, review_plan

    @staticmethod
    def _require_run_owner(
        *,
        run: dict[str, Any],
        user_id: UUID,
    ) -> None:
        run_user_id = run.get("user_id")

        if run_user_id is None:
            raise CustomerSupportReviewPlanLineageError(
                "Original workflow run has no owner"
            )

        if str(run_user_id) != str(user_id):
            raise CustomerSupportReviewPlanLineageError(
                "Original workflow run ownership mismatch"
            )

    @staticmethod
    def _require_outcome_lineage(
        *,
        outcome: CustomerSupportOutcomeRecord,
        review_plan_id: str,
        review_plan: SupportReviewPlan,
        run: dict[str, Any],
    ) -> None:
        if outcome.review_plan_id != review_plan_id:
            raise CustomerSupportReviewPlanLineageError(
                "Support outcome review-plan identity "
                "does not match the original workflow"
            )

        if str(run.get("workflow_run_id")) != str(
            outcome.workflow_run_id
        ):
            raise CustomerSupportReviewPlanLineageError(
                "Loaded workflow run identity does not "
                "match the support outcome"
            )

        if (
            outcome.source_objective_version
            != review_plan.source_objective_version
        ):
            raise CustomerSupportReviewPlanLineageError(
                "Support outcome objective version does "
                "not match the original review plan"
            )

        if outcome.order_ref != review_plan.order_ref:
            raise CustomerSupportReviewPlanLineageError(
                "Support outcome order identity does not "
                "match the original review plan"
            )

    @staticmethod
    def _uuid(
        value: str,
        field_name: str,
    ) -> UUID:
        try:
            return UUID(str(value).strip())
        except (
            AttributeError,
            TypeError,
            ValueError,
        ) as exc:
            raise CustomerSupportReviewPlanLineageError(
                f"{field_name} must contain a UUID"
            ) from exc

    @staticmethod
    def _required_text(
        value: Any,
        field_name: str,
    ) -> str:
        normalized = str(value or "").strip()

        if not normalized:
            raise CustomerSupportReviewPlanLineageError(
                f"{field_name} is required"
            )

        return normalized


__all__ = [
    "CustomerSupportReviewPlanLineageError",
    "CustomerSupportReviewPlanLoader",
    "CustomerSupportReviewPlanNotFoundError",
    "LoadedCustomerSupportReviewPlan",
]
