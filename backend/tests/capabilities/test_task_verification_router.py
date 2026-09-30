from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.api.auth import get_current_user
from app.runtime.capabilities.execution.verification import (
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationRepository,
    TaskVerificationRequest,
    TaskVerificationResult,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


def request_payload(
    *,
    verification_id,
    idempotency_key,
):
    return {
        "verification_id": verification_id,
        "idempotency_key": idempotency_key,
        "capability_id": (
            "ecommerce.orders.manage"
        ),
        "provider_id": "shopify",
        "provider_ref": (
            "shopify.order_action"
        ),
        "action": "refund",
        "tenant_id": "tenant-api",
        "correlation_id": (
            f"correlation-{uuid4()}"
        ),
        "workflow_run_id": "run-api",
        "task_id": "task-api",
        "inputs": {
            "action": "refund",
            "order_ref": "#5001",
            "amount": "25.00",
        },
        "expected_outcome": {
            "refund_completed": True,
        },
        "execution_output": {
            "status": "prepared",
            "payload": {
                "status": "prepared",
                "order_id": "5001",
                "amount": "25.00",
            },
        },
        "metadata": {
            "source": "api-test",
        },
    }


@pytest.mark.asyncio
async def test_task_verification_create_list_get_and_attempts():
    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/capabilities/task-verifications",
                json=request_payload(
                    verification_id=(
                        verification_id
                    ),
                    idempotency_key=(
                        f"api:{verification_id}:1"
                    ),
                ),
            )

            assert created.status_code == 201
            body = created.json()

            assert body["created"] is True
            assert body["attempt_number"] == 1
            assert (
                body["result"]["outcome"]
                == "partially_verified"
            )

            record_id = body["record_id"]

            listed = await client.get(
                "/capabilities/task-verifications",
                params={
                    "tenant_id": "tenant-api",
                    "outcome": (
                        "partially_verified"
                    ),
                },
            )

            assert listed.status_code == 200
            items = listed.json()["items"]

            assert len(items) == 1
            assert items[0]["id"] == record_id

            fetched = await client.get(
                "/capabilities/"
                "task-verifications/"
                f"record/{record_id}"
            )

            assert fetched.status_code == 200
            assert (
                fetched.json()[
                    "verification_id"
                ]
                == verification_id
            )

            attempts = await client.get(
                "/capabilities/"
                "task-verifications/"
                f"{verification_id}/attempts"
            )

            assert attempts.status_code == 200
            assert len(
                attempts.json()["items"]
            ) == 1
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_task_verification_create_rejects_user_id():
    user_id = uuid4()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    payload = request_payload(
        verification_id=f"verify-{uuid4()}",
        idempotency_key=f"api:{uuid4()}",
    )
    payload["user_id"] = str(uuid4())

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/capabilities/task-verifications",
                json=payload,
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_task_verification_reads_are_user_scoped():
    owner_id = uuid4()
    other_user_id = uuid4()
    verification_id = f"verify-{uuid4()}"

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(owner_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/capabilities/task-verifications",
                json=request_payload(
                    verification_id=(
                        verification_id
                    ),
                    idempotency_key=(
                        f"api:{verification_id}:1"
                    ),
                ),
            )

        record_id = created.json()[
            "record_id"
        ]
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(other_user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            fetched = await client.get(
                "/capabilities/"
                "task-verifications/"
                f"record/{record_id}"
            )
            attempts = await client.get(
                "/capabilities/"
                "task-verifications/"
                f"{verification_id}/attempts"
            )
            listed = await client.get(
                "/capabilities/task-verifications"
            )

        assert fetched.status_code == 404
        assert attempts.status_code == 404
        assert listed.status_code == 200
        assert listed.json()["items"] == []
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_retry_requires_latest_retryable_attempt():
    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/capabilities/task-verifications",
                json=request_payload(
                    verification_id=(
                        verification_id
                    ),
                    idempotency_key=(
                        f"api:{verification_id}:1"
                    ),
                ),
            )

            assert created.status_code == 201

            retry = await client.post(
                "/capabilities/"
                "task-verifications/"
                f"{verification_id}/retry",
                json={
                    "idempotency_key": (
                        f"api:{verification_id}:2"
                    )
                },
            )

        assert retry.status_code == 409
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_retry_reconstructs_request_and_creates_next_attempt():
    user_id = uuid4()
    verification_id = f"verify-{uuid4()}"

    async with SessionLocal() as db:
        repo = TaskVerificationRepository(db)

        request = TaskVerificationRequest(
            verification_id=verification_id,
            capability_id=(
                "ecommerce.orders.manage"
            ),
            provider_id="shopify",
            provider_ref=(
                "shopify.order_action"
            ),
            action="refund",
            user_id=str(user_id),
            tenant_id="tenant-retry",
            correlation_id="correlation-retry",
            workflow_run_id="run-retry",
            task_id="task-retry",
            inputs={
                "action": "refund",
                "order_ref": "#5002",
                "amount": "20.00",
            },
            expected_outcome={
                "refund_completed": True,
            },
            execution_output={
                "status": "unknown",
            },
            metadata={
                "source": "retry-test",
            },
        )

        result = TaskVerificationResult(
            verification_id=verification_id,
            capability_id=(
                request.capability_id
            ),
            provider_id=request.provider_id,
            provider_ref=request.provider_ref,
            action=request.action,
            outcome=(
                TaskVerificationOutcome
                .INCONCLUSIVE
            ),
            method=(
                TaskVerificationMethod
                .EXECUTION_EVIDENCE
            ),
            reason_code=(
                "refund_preparation_status_unknown"
            ),
            summary="Retryable test attempt",
            confidence=0.0,
            retryable=True,
            observed_outcome={},
            evidence=[],
        )

        await repo.append_attempt(
            user_id=user_id,
            request=request,
            result=result,
            idempotency_key=(
                f"seed:{verification_id}:1"
            ),
        )
        await db.commit()

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            retry = await client.post(
                "/capabilities/"
                "task-verifications/"
                f"{verification_id}/retry",
                json={
                    "idempotency_key": (
                        f"api:{verification_id}:2"
                    )
                },
            )

            assert retry.status_code == 201
            body = retry.json()

            assert body["attempt_number"] == 2
            assert body["created"] is True

            attempts = await client.get(
                "/capabilities/"
                "task-verifications/"
                f"{verification_id}/attempts"
            )

            assert attempts.status_code == 200
            rows = attempts.json()["items"]

            assert [
                item["attempt_number"]
                for item in rows
            ] == [1, 2]
            assert (
                rows[1]["correlation_id"]
                == "correlation-retry"
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
