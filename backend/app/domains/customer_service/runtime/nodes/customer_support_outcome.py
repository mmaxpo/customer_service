from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domains.customer_service.services.support.outcome.customer_support_outcome import (
    CustomerSupportOutcomeProjector,
)


class CustomerSupportOutcomeProjectionConfig(BaseModel):
    node_type: Literal[
        "customer_service.project_support_outcome"
    ] = "customer_service.project_support_outcome"

    support_review_key: str = Field(
        default="support_review"
    )
    approval_result_key: str = Field(
        default="approval_result"
    )
    prepared_operations_key: str = Field(
        default="prepared_operations"
    )

    save_as: str = Field(default="support_outcome")
    message_save_as: str = Field(
        default="customer_message"
    )


class CustomerSupportOutcomeProjectionNode:
    async def run(
        self,
        ctx,
        state: dict[str, Any],
        config: CustomerSupportOutcomeProjectionConfig,
    ) -> dict[str, Any]:
        vars_ = state.get("vars") or {}

        support_review = vars_.get(
            config.support_review_key
        )
        if not isinstance(support_review, dict):
            raise ValueError(
                "customer_service.project_support_outcome "
                "requires support_review"
            )

        review_plan_id = str(
            support_review.get("review_plan_id") or ""
        ).strip()

        if not review_plan_id:
            raise ValueError(
                "customer_service.project_support_outcome "
                "requires review_plan_id"
            )

        approval_result = bool(
            vars_.get(config.approval_result_key)
        )

        prepared_operations = vars_.get(
            config.prepared_operations_key
        )

        if not isinstance(prepared_operations, dict):
            prepared_operations = {}

        outcome = CustomerSupportOutcomeProjector().project(
            review_plan_id=review_plan_id,
            support_review=support_review,
            approval_result=approval_result,
            prepared_operations=prepared_operations,
        )

        output = outcome.model_dump(mode="json")

        return {
            "output": output,
            "patch": {
                "vars": {
                    config.save_as: output,
                    config.message_save_as: (
                        outcome.customer_message
                    ),
                },
                "last": output,
            },
            "meta": {
                "review_plan_id": outcome.review_plan_id,
                "decision": outcome.decision,
                "operation_count": len(outcome.operations),
            },
        }
