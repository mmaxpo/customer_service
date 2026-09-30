from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.session import SessionLocal
from app.runtime.capabilities.execution.verification import (
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationRepository,
    TaskVerificationRequest,
    TaskVerificationResult,
)


def request_for(
    *,
    user_id,
    verification_id,
    tenant_id=None,
    correlation_id=None,
    workflow_run_id=None,
    task_id=None,
):
    return TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=(
            "ecommerce.orders.manage"
        ),
        provider_id="shopify",
        provider_ref=(
            "shopify.order_action"
        ),
        action="cancel",
        user_id=str(user_id),
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        workflow_run_id=workflow_run_id,
        task_id=task_id,
        inputs={
            "action": "cancel",
            "order_ref": "#3001",
        },
        expected_outcome={
            "order_cancelled": True,
        },
        execution_output={
            "status": "cancelled",
        },
        metadata={
            "source": "contract_test",
        },
    )


def result_for(
    request,
    *,
    outcome=TaskVerificationOutcome.VERIFIED,
    retryable=False,
    reason_code="shopify_order_cancelled",
):
    return TaskVerificationResult(
        verification_id=(
            request.verification_id
        ),
        capability_id=(
            request.capability_id
        ),
        provider_id=request.provider_id,
        provider_ref=request.provider_ref,
        action=request.action,
        outcome=outcome,
        method=(
            TaskVerificationMethod.REMOTE_STATE
        ),
        reason_code=reason_code,
        summary="Verification result",
        confidence=1.0,
        retryable=retryable,
        observed_outcome={
            "order_cancelled": (
                outcome
                == TaskVerificationOutcome.VERIFIED
            ),
        },
        evidence=[],
    )


@pytest.mark.asyncio
async def test_task_verification_attempt_is_durable():
    user_id = uuid4()
    verification_id = f"verification-{uuid4()}"
    correlation_id = f"correlation-{uuid4()}"

    async with SessionLocal() as db:
        repo = TaskVerificationRepository(db)
        request = request_for(
            user_id=user_id,
            verification_id=verification_id,
            tenant_id="tenant-a",
            correlation_id=correlation_id,
            workflow_run_id="run-a",
            task_id="task-a",
        )

        row = await repo.append_attempt(
            user_id=user_id,
            request=request,
            result=result_for(request),
            idempotency_key=(
                f"verify:{verification_id}:1"
            ),
        )

        assert row.attempt_number == 1
        assert row.outcome == "verified"
        assert row.inputs_json["order_ref"] == "#3001"
        assert (
            row.requested_outcome_json[
                "order_cancelled"
            ]
            is True
        )
        assert (
            row.observed_outcome_json[
                "order_cancelled"
            ]
            is True
        )

        record_id = row.id
        await db.commit()

    async with SessionLocal() as db:
        persisted = await (
            TaskVerificationRepository(db)
            .get(
                user_id=user_id,
                record_id=record_id,
            )
        )

        assert persisted is not None
        assert (
            persisted.correlation_id
            == correlation_id
        )
        assert (
            persisted.workflow_run_id
            == "run-a"
        )
        assert persisted.task_id == "task-a"


@pytest.mark.asyncio
async def test_task_verification_idempotency_returns_existing_attempt():
    user_id = uuid4()
    verification_id = f"verification-{uuid4()}"
    key = f"verify:{verification_id}:same"

    async with SessionLocal() as db:
        repo = TaskVerificationRepository(db)
        request = request_for(
            user_id=user_id,
            verification_id=verification_id,
        )
        result = result_for(request)

        first = await repo.append_attempt(
            user_id=user_id,
            request=request,
            result=result,
            idempotency_key=key,
        )
        second = await repo.append_attempt(
            user_id=user_id,
            request=request,
            result=result,
            idempotency_key=key,
        )

        assert second.id == first.id
        assert second.attempt_number == 1

        rows = await repo.list_attempts(
            user_id=user_id,
            verification_id=verification_id,
        )

        assert len(rows) == 1
        await db.rollback()


@pytest.mark.asyncio
async def test_task_verification_retry_increments_attempt_number():
    user_id = uuid4()
    verification_id = f"verification-{uuid4()}"

    async with SessionLocal() as db:
        repo = TaskVerificationRepository(db)
        request = request_for(
            user_id=user_id,
            verification_id=verification_id,
        )

        first = await repo.append_attempt(
            user_id=user_id,
            request=request,
            result=result_for(
                request,
                outcome=(
                    TaskVerificationOutcome
                    .INCONCLUSIVE
                ),
                retryable=True,
                reason_code=(
                    "remote_observation_failed"
                ),
            ),
            idempotency_key=(
                f"verify:{verification_id}:1"
            ),
        )

        second = await repo.append_attempt(
            user_id=user_id,
            request=request,
            result=result_for(request),
            idempotency_key=(
                f"verify:{verification_id}:2"
            ),
        )

        assert first.attempt_number == 1
        assert second.attempt_number == 2

        rows = await repo.list_attempts(
            user_id=user_id,
            verification_id=verification_id,
        )

        assert [
            row.attempt_number
            for row in rows
        ] == [1, 2]

        assert [
            row.outcome
            for row in rows
        ] == [
            "inconclusive",
            "verified",
        ]

        await db.rollback()


@pytest.mark.asyncio
async def test_task_verification_reads_are_user_scoped():
    owner_id = uuid4()
    other_user_id = uuid4()
    verification_id = f"verification-{uuid4()}"

    async with SessionLocal() as db:
        repo = TaskVerificationRepository(db)
        request = request_for(
            user_id=owner_id,
            verification_id=verification_id,
        )

        row = await repo.append_attempt(
            user_id=owner_id,
            request=request,
            result=result_for(request),
            idempotency_key=(
                f"verify:{verification_id}:1"
            ),
        )

        assert (
            await repo.get(
                user_id=other_user_id,
                record_id=row.id,
            )
            is None
        )

        assert (
            await repo.list_attempts(
                user_id=other_user_id,
                verification_id=verification_id,
            )
            == []
        )

        await db.rollback()


@pytest.mark.asyncio
async def test_task_verification_list_filters_and_paginates():
    user_id = uuid4()
    tenant_a = f"tenant-a-{uuid4()}"
    tenant_b = f"tenant-b-{uuid4()}"

    async with SessionLocal() as db:
        repo = TaskVerificationRepository(db)

        for index, tenant_id in enumerate(
            [tenant_a, tenant_b, tenant_a],
            start=1,
        ):
            verification_id = (
                f"verification-{uuid4()}"
            )
            request = request_for(
                user_id=user_id,
                verification_id=(
                    verification_id
                ),
                tenant_id=tenant_id,
            )

            await repo.append_attempt(
                user_id=user_id,
                request=request,
                result=result_for(
                    request,
                    outcome=(
                        TaskVerificationOutcome
                        .INCONCLUSIVE
                        if index == 2
                        else TaskVerificationOutcome
                        .VERIFIED
                    ),
                    retryable=(index == 2),
                    reason_code=(
                        "remote_observation_failed"
                        if index == 2
                        else "shopify_order_cancelled"
                    ),
                ),
                idempotency_key=(
                    f"verify:{verification_id}:1"
                ),
            )

        tenant_rows = await repo.list_for_user(
            user_id=user_id,
            tenant_id=tenant_a,
            outcome="verified",
            limit=10,
            offset=0,
        )

        assert len(tenant_rows) == 2
        assert all(
            row.tenant_id == tenant_a
            for row in tenant_rows
        )

        first_page = await repo.list_for_user(
            user_id=user_id,
            limit=2,
            offset=0,
        )
        second_page = await repo.list_for_user(
            user_id=user_id,
            limit=2,
            offset=2,
        )

        assert len(first_page) == 2
        assert len(second_page) == 1
        assert {
            row.id
            for row in first_page
        }.isdisjoint(
            {
                row.id
                for row in second_page
            }
        )

        await db.rollback()


@pytest.mark.asyncio
async def test_task_verification_append_is_caller_transactional():
    user_id = uuid4()
    verification_id = f"verification-{uuid4()}"
    record_id = None

    async with SessionLocal() as db:
        repo = TaskVerificationRepository(db)
        request = request_for(
            user_id=user_id,
            verification_id=verification_id,
        )

        row = await repo.append_attempt(
            user_id=user_id,
            request=request,
            result=result_for(request),
            idempotency_key=(
                f"verify:{verification_id}:1"
            ),
        )
        record_id = row.id

        assert (
            await repo.get(
                user_id=user_id,
                record_id=record_id,
            )
            is not None
        )

        await db.rollback()

    async with SessionLocal() as db:
        assert (
            await TaskVerificationRepository(
                db
            ).get(
                user_id=user_id,
                record_id=record_id,
            )
            is None
        )


def test_task_verification_rejects_invalid_user_id():
    with pytest.raises(
        ValueError,
        match="valid UUID",
    ):
        from app.runtime.capabilities.execution.verification import (
            normalize_verification_user_id,
        )

        normalize_verification_user_id(
            "not-a-uuid"
        )
