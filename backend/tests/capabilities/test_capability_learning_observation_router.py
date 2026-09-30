from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.session import SessionLocal
from app.main import app
from app.platform.events.event_store import (
    PlatformEventStore,
)
from app.api.auth import get_current_user
from app.runtime.capabilities.execution.learning import (
    CapabilityLearningObservationProjector,
)
from app.runtime.capabilities.execution.verification import (
    TASK_VERIFICATION_COMPLETED_EVENT,
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationRepository,
    TaskVerificationRequest,
    TaskVerificationResult,
)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


async def create_learning_observation(
    *,
    db,
    user_id,
    tenant_id: str,
    capability_id: str,
    provider_id: str,
    action: str,
    outcome: TaskVerificationOutcome,
    retryable: bool,
):
    verification_id = (
        f"learning-router-{uuid4()}"
    )

    request = TaskVerificationRequest(
        verification_id=verification_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=(
            f"{provider_id}.order_action"
        ),
        action=action,
        user_id=str(user_id),
        tenant_id=tenant_id,
        correlation_id=(
            f"correlation-{verification_id}"
        ),
        workflow_run_id=(
            f"workflow-{verification_id}"
        ),
        task_id=f"task-{verification_id}",
    )

    result = TaskVerificationResult(
        verification_id=verification_id,
        capability_id=capability_id,
        provider_id=provider_id,
        provider_ref=request.provider_ref,
        action=action,
        outcome=outcome,
        method=(
            TaskVerificationMethod
            .REMOTE_STATE
        ),
        reason_code=outcome.value,
        summary=f"Outcome: {outcome.value}",
        confidence=(
            0.2 if retryable else 1.0
        ),
        retryable=retryable,
        observed_outcome={
            "status": outcome.value,
        },
    )

    record = await (
        TaskVerificationRepository(
            db
        ).append_attempt(
            user_id=user_id,
            request=request,
            result=result,
            idempotency_key=(
                f"{verification_id}:attempt:1"
            ),
        )
    )
    await db.commit()
    await db.refresh(record)

    event = await PlatformEventStore(
        db
    ).append(
        user_id=user_id,
        event_type=(
            TASK_VERIFICATION_COMPLETED_EVENT
        ),
        source="runtime.task_verification",
        payload={
            "record_id": str(record.id),
            "verification_id": (
                record.verification_id
            ),
        },
        meta={
            "tenant_id": tenant_id,
        },
    )

    projected = await (
        CapabilityLearningObservationProjector(
            db
        ).project_event(event)
    )

    return UUID(
        projected[
            "learning_observation_id"
        ]
    )


@pytest.mark.asyncio
async def test_learning_observation_routes_scope_to_current_user():
    owner_id = uuid4()
    other_id = uuid4()

    async with SessionLocal() as db:
        owner_record_id = await (
            create_learning_observation(
                db=db,
                user_id=owner_id,
                tenant_id="tenant-owner",
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                action="refund",
                outcome=(
                    TaskVerificationOutcome
                    .VERIFIED
                ),
                retryable=False,
            )
        )

        other_record_id = await (
            create_learning_observation(
                db=db,
                user_id=other_id,
                tenant_id="tenant-other",
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                action="cancel",
                outcome=(
                    TaskVerificationOutcome
                    .INCONCLUSIVE
                ),
                retryable=True,
            )
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(owner_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "learning-observations"
            )

            assert response.status_code == 200

            body = response.json()

            returned_ids = {
                item["id"]
                for item in body["items"]
            }

            assert str(owner_record_id) in (
                returned_ids
            )
            assert str(other_record_id) not in (
                returned_ids
            )

            owner_response = await client.get(
                "/capabilities/"
                "learning-observations/"
                f"record/{owner_record_id}"
            )

            assert (
                owner_response.status_code
                == 200
            )
            assert (
                owner_response.json()["id"]
                == str(owner_record_id)
            )

            hidden_response = await client.get(
                "/capabilities/"
                "learning-observations/"
                f"record/{other_record_id}"
            )

            assert (
                hidden_response.status_code
                == 404
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_learning_observation_list_filters_and_paginates():
    user_id = uuid4()

    async with SessionLocal() as db:
        verified_id = await (
            create_learning_observation(
                db=db,
                user_id=user_id,
                tenant_id="tenant-filter",
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                action="refund",
                outcome=(
                    TaskVerificationOutcome
                    .VERIFIED
                ),
                retryable=False,
            )
        )

        await create_learning_observation(
            db=db,
            user_id=user_id,
            tenant_id="tenant-filter",
            capability_id=(
                "ecommerce.orders.manage"
            ),
            provider_id="shopify",
            action="cancel",
            outcome=(
                TaskVerificationOutcome
                .INCONCLUSIVE
            ),
            retryable=True,
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "learning-observations",
                params={
                    "tenant_id": (
                        "tenant-filter"
                    ),
                    "action": "refund",
                    "outcome": "verified",
                    "is_final": "true",
                    "retryable": "false",
                    "limit": 1,
                    "offset": 0,
                },
            )

            assert response.status_code == 200

            body = response.json()

            assert body["limit"] == 1
            assert body["offset"] == 0
            assert len(body["items"]) == 1
            assert (
                body["items"][0]["id"]
                == str(verified_id)
            )
            assert (
                body["items"][0]["action"]
                == "refund"
            )
            assert (
                body["items"][0]["outcome"]
                == "verified"
            )
            assert (
                body["items"][0]["is_final"]
                is True
            )
            assert (
                body["items"][0]["retryable"]
                is False
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_learning_observation_response_excludes_raw_verification_data():
    user_id = uuid4()

    async with SessionLocal() as db:
        record_id = await (
            create_learning_observation(
                db=db,
                user_id=user_id,
                tenant_id="tenant-safe",
                capability_id=(
                    "ecommerce.orders.manage"
                ),
                provider_id="shopify",
                action="refund",
                outcome=(
                    TaskVerificationOutcome
                    .VERIFIED
                ),
                retryable=False,
            )
        )

    app.dependency_overrides[
        get_current_user
    ] = lambda: FakeUser(user_id)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/capabilities/"
                "learning-observations/"
                f"record/{record_id}"
            )

            assert response.status_code == 200

            body = response.json()

            assert "inputs_json" not in body
            assert (
                "execution_output_json"
                not in body
            )
            assert "evidence_json" not in body
            assert (
                "request_metadata_json"
                not in body
            )

            assert (
                "observed_outcome_json"
                in body
            )
            assert (
                "evidence_summary_json"
                in body
            )
            assert "context_json" in body
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )
