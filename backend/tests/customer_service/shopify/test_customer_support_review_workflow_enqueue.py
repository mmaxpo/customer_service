from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder

from app.core.session import SessionLocal
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.domains.customer_service.services.support.planning.customer_support_review_workflow import (
    CustomerSupportReviewWorkflowBuilder,
)
from app.platform.jobs.service import JobService


def _plan() -> SupportReviewPlan:
    return SupportReviewPlan(
        order_ref="#1003",
        provider="shopify",
        provider_order_id="1003",
        operations=[
            SupportReviewOperation(
                operation_type=(SupportReviewOperationType.PARTIAL_REFUND),
                item_id="101",
                item_label="Snowboard",
            ),
            SupportReviewOperation(
                operation_type=(SupportReviewOperationType.REPLACEMENT),
                item_id="102",
                item_label="Snowboard Boots",
            ),
            SupportReviewOperation(
                operation_type=(SupportReviewOperationType.REPLACEMENT_ADDRESS),
                address={"formatted": ("123 Main Street, Miami, FL 33101")},
            ),
        ],
    )


@pytest.mark.asyncio
async def test_support_review_workflow_enqueue_is_idempotent():
    user_id = uuid4()
    session_id = uuid4()
    review_plan_id = str(uuid4())

    builder = CustomerSupportReviewWorkflowBuilder()
    plan = _plan()

    workflow = builder.build(
        review_plan_id=review_plan_id,
        review_plan=plan,
    )

    payload = jsonable_encoder(
        {
            "workflow": workflow,
            "message": (
                f"Customer support resolution ready for review: {review_plan_id}"
            ),
            "thread_id": str(session_id),
            "extras": {
                "customer_service": True,
                "support_review": (
                    builder.support_review_extras(
                        review_plan_id=review_plan_id,
                        review_plan=plan,
                    )
                ),
            },
        }
    )

    idempotency_key = builder.workflow_job_idempotency_key(
        review_plan_id=review_plan_id,
    )

    async with SessionLocal() as db:
        jobs = JobService(db)

        first = await jobs.enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload=payload,
            idempotency_key=idempotency_key,
        )

        second = await jobs.enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload=payload,
            idempotency_key=idempotency_key,
        )

        assert first.id == second.id
        assert first.job_type == "workflow.run"
        assert first.status == "queued"
        assert first.idempotency_key == idempotency_key

        support_review = first.payload["extras"]["support_review"]

        assert support_review["review_plan_id"] == (review_plan_id)
        assert support_review["review_plan"]["order_ref"] == ("#1003")
