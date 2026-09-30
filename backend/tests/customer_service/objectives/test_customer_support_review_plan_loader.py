from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperation,
    SupportReviewOperationType,
    SupportReviewPlan,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan_loader import (
    CustomerSupportReviewPlanLineageError,
    CustomerSupportReviewPlanLoader,
    CustomerSupportReviewPlanNotFoundError,
)
from app.models.models import ObjectiveResolutionRecord
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.runtime.engine.persistence.postgres import (
    PostgresRunStore,
)


def _plan() -> SupportReviewPlan:
    return SupportReviewPlan(
        order_ref="#1001",
        provider="shopify",
        provider_order_id=(
            "gid://shopify/Order/1001"
        ),
        operations=[
            SupportReviewOperation(
                operation_ref=(
                    "support_operation:001:"
                    "partial_refund:line-1"
                ),
                operation_type=(
                    SupportReviewOperationType
                    .PARTIAL_REFUND
                ),
                item_id="line-1",
                item_label="Snowboard",
                approval_required=True,
                execution_allowed=False,
            ),
            SupportReviewOperation(
                operation_ref=(
                    "support_operation:002:"
                    "replacement:line-2"
                ),
                operation_type=(
                    SupportReviewOperationType
                    .REPLACEMENT
                ),
                item_id="line-2",
                item_label="Boots",
                approval_required=True,
                execution_allowed=False,
            ),
            SupportReviewOperation(
                operation_ref=(
                    "support_operation:003:"
                    "replacement_address:address"
                ),
                operation_type=(
                    SupportReviewOperationType
                    .REPLACEMENT_ADDRESS
                ),
                address={
                    "address1": "123 Main Street",
                    "city": "Miami",
                    "province": "FL",
                    "zip": "33101",
                    "country": "US",
                },
                approval_required=True,
                execution_allowed=False,
            ),
        ],
        approval_required=True,
        execution_allowed=False,
        source_objective_version=3,
    )


def _workflow(
    *,
    review_plan_id: str,
    plan: SupportReviewPlan,
) -> dict:
    support_review = {
        "review_plan_id": review_plan_id,
        "review_plan": plan.model_dump(
            mode="json"
        ),
    }

    return {
        "name": (
            f"Customer Support Review "
            f"{review_plan_id}"
        ),
        "version": "1.0.0",
        "nodes": [],
        "edges": [],
        "metadata": {
            "kind": "customer_support_review",
            "review_plan_id": review_plan_id,
            "approval_required": True,
            "provider": plan.provider,
            "order_ref": plan.order_ref,
            "support_review": support_review,
        },
    }


async def _persist_lineage(
    db,
    *,
    user_id,
    run_user_id=None,
    workflow=None,
):
    review_plan_id = str(uuid4())
    support_outcome_id = uuid4()
    resolution_record_id = uuid4()
    workflow_run_id = uuid4()
    plan = _plan()

    await PostgresRunStore(db).create_run(
        run_id=workflow_run_id,
        user_id=(
            run_user_id
            if run_user_id is not None
            else user_id
        ),
        thread_id=None,
        workflow=(
            workflow
            if workflow is not None
            else _workflow(
                review_plan_id=review_plan_id,
                plan=plan,
            )
        ),
        state={
            "workflow_run_id": str(
                workflow_run_id
            ),
            "vars": {},
        },
        status="completed",
        extra={},
    )

    outcome = CustomerSupportOutcomeRecord(
        id=support_outcome_id,
        user_id=user_id,
        review_plan_id=review_plan_id,
        workflow_run_id=workflow_run_id,
        chat_session_id=uuid4(),
        conversation_id=uuid4(),
        objective_namespace=(
            "customer_service.support"
        ),
        objective_ref=review_plan_id,
        source_objective_version=(
            plan.source_objective_version
        ),
        outcome_version=1,
        objective_type="multi_operation",
        order_ref=plan.order_ref,
        decision="approved",
        status="failed",
        operation_count=2,
        customer_message=(
            "One support operation failed."
        ),
        operations_json=[],
        outcome_json={
            "version": 1,
            "review_plan_id": review_plan_id,
            "order_ref": plan.order_ref,
            "decision": "approved",
            "operations": [],
            "customer_message": (
                "One support operation failed."
            ),
        },
    )
    db.add(outcome)

    source_event = await PlatformEventStore(
        db
    ).append(
        event_type=(
            "customer_service.support."
            "outcome.evaluated"
        ),
        source=(
            "customer_service."
            "support_outcome_evaluation"
        ),
        user_id=user_id,
        payload={
            "support_outcome_id": str(
                support_outcome_id
            ),
            "review_plan_id": review_plan_id,
        },
        meta={
            "workflow_run_id": str(
                workflow_run_id
            ),
        },
        commit=False,
    )

    resolution = ObjectiveResolutionRecord(
        id=resolution_record_id,
        source_event_id=source_event.id,
        user_id=user_id,
        tenant_id="tenant-1",
        objective_namespace=(
            "customer_service.support"
        ),
        objective_type="multi_operation",
        objective_ref=review_plan_id,
        objective_version=(
            plan.source_objective_version
        ),
        source_outcome_ref=str(
            support_outcome_id
        ),
        outcome_version=1,
        source_evaluation_ref=str(uuid4()),
        evaluation_version=1,
        projection_version=1,
        assessment_schema_version=(
            "objective_resolution_assessment.v1"
        ),
        workflow_run_id=str(
            workflow_run_id
        ),
        status="failed",
        reason_code=(
            "one_or_more_operations_failed"
        ),
        summary=(
            "One required support operation failed."
        ),
        confidence=0.9,
        is_terminal=False,
        operation_count=2,
        achieved_operation_count=1,
        unresolved_operation_count=1,
        failed_operation_count=1,
        pending_operation_count=0,
        unknown_operation_count=0,
        not_executed_operation_count=0,
        assessment_json={
            "schema_version": (
                "objective_resolution_assessment.v1"
            ),
            "objective": {
                "namespace": (
                    "customer_service.support"
                ),
                "objective_type": (
                    "multi_operation"
                ),
                "objective_ref": review_plan_id,
                "objective_version": (
                    plan.source_objective_version
                ),
            },
        },
    )
    db.add(resolution)

    await db.commit()

    return {
        "review_plan_id": review_plan_id,
        "support_outcome_id": (
            support_outcome_id
        ),
        "resolution_record_id": (
            resolution_record_id
        ),
        "workflow_run_id": workflow_run_id,
        "plan": plan,
    }


@pytest.mark.asyncio
async def test_loads_complete_plan_for_resolution():
    user_id = uuid4()

    async with SessionLocal() as db:
        lineage = await _persist_lineage(
            db,
            user_id=user_id,
        )

        loaded = await (
            CustomerSupportReviewPlanLoader(db)
            .load_for_resolution(
                user_id=user_id,
                resolution_record_id=(
                    lineage[
                        "resolution_record_id"
                    ]
                ),
            )
        )

    assert loaded.review_plan_id == (
        lineage["review_plan_id"]
    )
    assert loaded.review_plan == lineage["plan"]
    assert loaded.support_outcome_id == (
        lineage["support_outcome_id"]
    )
    assert loaded.workflow_run_id == (
        lineage["workflow_run_id"]
    )
    assert loaded.resolution_record_id == (
        lineage["resolution_record_id"]
    )

    replacement_address = (
        loaded.review_plan.operations[2].address
    )

    assert replacement_address == {
        "address1": "123 Main Street",
        "city": "Miami",
        "province": "FL",
        "zip": "33101",
        "country": "US",
    }


@pytest.mark.asyncio
async def test_loads_complete_plan_for_outcome():
    user_id = uuid4()

    async with SessionLocal() as db:
        lineage = await _persist_lineage(
            db,
            user_id=user_id,
        )

        loaded = await (
            CustomerSupportReviewPlanLoader(db)
            .load_for_outcome(
                user_id=user_id,
                support_outcome_id=(
                    lineage["support_outcome_id"]
                ),
            )
        )

    assert loaded.review_plan == lineage["plan"]
    assert loaded.resolution_record_id is None


@pytest.mark.asyncio
async def test_outcome_lookup_is_user_scoped():
    owner_id = uuid4()
    other_user_id = uuid4()

    async with SessionLocal() as db:
        lineage = await _persist_lineage(
            db,
            user_id=owner_id,
        )

        with pytest.raises(
            CustomerSupportReviewPlanNotFoundError,
            match="outcome was not found",
        ):
            await (
                CustomerSupportReviewPlanLoader(db)
                .load_for_outcome(
                    user_id=other_user_id,
                    support_outcome_id=(
                        lineage[
                            "support_outcome_id"
                        ]
                    ),
                )
            )


@pytest.mark.asyncio
async def test_workflow_run_owner_is_verified():
    user_id = uuid4()
    wrong_run_owner = uuid4()

    async with SessionLocal() as db:
        lineage = await _persist_lineage(
            db,
            user_id=user_id,
            run_user_id=wrong_run_owner,
        )

        with pytest.raises(
            CustomerSupportReviewPlanLineageError,
            match="ownership mismatch",
        ):
            await (
                CustomerSupportReviewPlanLoader(db)
                .load_for_resolution(
                    user_id=user_id,
                    resolution_record_id=(
                        lineage[
                            "resolution_record_id"
                        ]
                    ),
                )
            )


@pytest.mark.asyncio
async def test_review_plan_identity_conflict_is_rejected():
    user_id = uuid4()
    plan = _plan()
    review_plan_id = str(uuid4())

    workflow = _workflow(
        review_plan_id=review_plan_id,
        plan=plan,
    )
    workflow["metadata"][
        "support_review"
    ]["review_plan_id"] = str(uuid4())

    async with SessionLocal() as db:
        lineage = await _persist_lineage(
            db,
            user_id=user_id,
            workflow=workflow,
        )

        with pytest.raises(
            CustomerSupportReviewPlanLineageError,
            match="identities conflict",
        ):
            await (
                CustomerSupportReviewPlanLoader(db)
                .load_for_outcome(
                    user_id=user_id,
                    support_outcome_id=(
                        lineage[
                            "support_outcome_id"
                        ]
                    ),
                )
            )


@pytest.mark.asyncio
async def test_invalid_plan_payload_is_rejected():
    user_id = uuid4()
    review_plan_id = str(uuid4())

    workflow = {
        "name": "Invalid support review",
        "version": "1.0.0",
        "nodes": [],
        "edges": [],
        "metadata": {
            "kind": "customer_support_review",
            "review_plan_id": review_plan_id,
            "support_review": {
                "review_plan_id": review_plan_id,
                "review_plan": {
                    "provider": "shopify",
                },
            },
        },
    }

    async with SessionLocal() as db:
        lineage = await _persist_lineage(
            db,
            user_id=user_id,
            workflow=workflow,
        )

        with pytest.raises(
            CustomerSupportReviewPlanLineageError,
            match="payload is invalid",
        ):
            await (
                CustomerSupportReviewPlanLoader(db)
                .load_for_outcome(
                    user_id=user_id,
                    support_outcome_id=(
                        lineage[
                            "support_outcome_id"
                        ]
                    ),
                )
            )


@pytest.mark.asyncio
async def test_resolution_objective_identity_is_verified():
    user_id = uuid4()

    async with SessionLocal() as db:
        lineage = await _persist_lineage(
            db,
            user_id=user_id,
        )

        resolution = await db.get(
            ObjectiveResolutionRecord,
            lineage["resolution_record_id"],
        )
        assert resolution is not None

        resolution.objective_ref = str(uuid4())
        await db.commit()

        with pytest.raises(
            CustomerSupportReviewPlanLineageError,
            match="resolution reference",
        ):
            await (
                CustomerSupportReviewPlanLoader(db)
                .load_for_resolution(
                    user_id=user_id,
                    resolution_record_id=(
                        lineage[
                            "resolution_record_id"
                        ]
                    ),
                )
            )
