from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.customer_service.services.support.outcome.customer_support_outcome import CustomerSupportOutcome
from app.domains.customer_service.services.support.outcome.customer_support_outcome_recording import (
    CustomerSupportOutcomeRecordingService,
)


class CustomerSupportOutcomeRecordingConfig(BaseModel):
    node_type: Literal["customer_service.record_support_outcome"] = (
        "customer_service.record_support_outcome"
    )
    outcome_key: str = Field(default="support_outcome")
    support_review_key: str = Field(default="support_review")
    chat_session_id_key: str = Field(default="customer_chat_session_id")
    save_as: str = Field(default="recorded_support_outcome")


class CustomerSupportOutcomeRecordingNode:
    async def run(self, ctx, state: dict[str, Any], config: CustomerSupportOutcomeRecordingConfig) -> dict[str, Any]:
        if ctx.db is None:
            raise RuntimeError("customer_service.record_support_outcome requires a database session")
        workflow_run_id = (
            getattr(ctx, "workflow_run_id", None)
            or state.get("workflow_run_id")
            or (state.get("meta") or {}).get("workflow_run_id")
        )

        if ctx.user_id is None or workflow_run_id is None:
            raise ValueError(
                "customer_service.record_support_outcome "
                "requires user_id and workflow_run_id"
            )

        vars_ = state.get("vars") or {}
        outcome = CustomerSupportOutcome.model_validate(vars_.get(config.outcome_key))
        support_review = vars_.get(config.support_review_key) or {}
        review_plan = support_review.get("review_plan") or {}
        source_objective_version = int(review_plan.get("source_objective_version") or 1)
        chat_session_id = UUID(str(vars_.get(config.chat_session_id_key)))
        runtime_meta = (ctx.node_data or {}).get("_runtime") or {}

        result = await CustomerSupportOutcomeRecordingService(ctx.db).record(
            user_id=UUID(str(ctx.user_id)),
            workflow_run_id=UUID(str(workflow_run_id)),
            chat_session_id=chat_session_id,
            outcome=outcome,
            source_objective_version=source_objective_version,
            recording_idempotency_key=runtime_meta.get("idempotency_key"),
        )

        output = {
            "outcome_id": str(result.record.id),
            "created": result.created,
            "event_id": str(result.event_id) if result.event_id else None,
            "review_plan_id": result.record.review_plan_id,
            "status": result.record.status,
        }
        return {
            "output": output,
            "patch": {"vars": {config.save_as: output}},
            "meta": output,
        }
