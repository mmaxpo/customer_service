from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

# Initialize the canonical SQLAlchemy model bootstrap before
# importing focused customer-service model modules.
from app.models.models import PlatformEvent

from app.core.session import SessionLocal
from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.repositories.chat_repository import (
    ChatRepository,
)
from app.domains.customer_service.repositories.customer_support_outcomes import (
    CustomerSupportOutcomeConflictError,
)
from app.domains.customer_service.services.support.outcome.customer_support_outcome import (
    CustomerSupportOutcome,
    SupportOperationOutcome,
    SupportOutcomeStatus,
)
from app.domains.customer_service.services.support.outcome.customer_support_outcome_recording import (
    SUPPORT_OUTCOME_RECORDED_EVENT,
    CustomerSupportOutcomeRecordingService,
)
from app.domains.customer_service.services.support.planning.customer_support_review_plan import (
    SupportReviewOperationType,
)
from app.main import app
from app.platform.events.publisher import PlatformEventPublisher
from app.api.auth import get_current_user


@dataclass(frozen=True)
class SupportOutcomeTestUser:
    id: UUID
    email: str


def _user(prefix: str) -> SupportOutcomeTestUser:
    identifier = uuid4()
    return SupportOutcomeTestUser(
        id=identifier,
        email=f"{prefix}-{identifier}@example.com",
    )


def _approved_outcome(
    *,
    review_plan_id: str,
    message: str = "Your refund was prepared.",
) -> CustomerSupportOutcome:
    return CustomerSupportOutcome(
        review_plan_id=review_plan_id,
        order_ref="1001",
        decision="approved",
        operations=[
            SupportOperationOutcome(
                operation_type=(
                    SupportReviewOperationType.WHOLE_REFUND
                ),
                status=SupportOutcomeStatus.PREPARED,
                prepared=True,
                provider_result={
                    "status": "prepared",
                    "prepared_only": True,
                },
            )
        ],
        customer_message=message,
    )


async def _create_linked_chat_session(
    user: SupportOutcomeTestUser,
) -> tuple[UUID, UUID]:
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            settings_response = await client.get(
                "/customer-service/chat/widget/settings"
            )
            assert settings_response.status_code == 200

            public_key = settings_response.json()["public_key"]

            session_response = await client.post(
                (
                    "/customer-service/chat/public/"
                    f"{public_key}/sessions"
                ),
                json={
                    "visitor_id": f"visitor-{uuid4()}",
                    "channel": "website",
                },
            )

            assert session_response.status_code == 200, (
                session_response.text
            )

            body = session_response.json()

            return (
                UUID(body["id"]),
                UUID(body["conversation_id"]),
            )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


async def _events_for(
    *,
    user_id: UUID,
    review_plan_id: str,
) -> list[PlatformEvent]:
    async with SessionLocal() as db:
        events = (
            await db.execute(
                select(PlatformEvent).where(
                    PlatformEvent.user_id == user_id,
                    PlatformEvent.event_type
                    == SUPPORT_OUTCOME_RECORDED_EVENT,
                )
            )
        ).scalars().all()

        return [
            event
            for event in events
            if event.payload.get("review_plan_id")
            == review_plan_id
        ]


@pytest.mark.asyncio
async def test_first_recording_creates_one_outcome_and_event():
    user = _user("support-outcome-first")
    chat_session_id, conversation_id = (
        await _create_linked_chat_session(user)
    )
    review_plan_id = str(uuid4())
    workflow_run_id = uuid4()

    async with SessionLocal() as db:
        result = await CustomerSupportOutcomeRecordingService(
            db
        ).record(
            user_id=user.id,
            workflow_run_id=workflow_run_id,
            chat_session_id=chat_session_id,
            outcome=_approved_outcome(
                review_plan_id=review_plan_id
            ),
            source_objective_version=3,
            recording_idempotency_key=(
                f"record:{review_plan_id}"
            ),
        )

    assert result.created is True
    assert result.event_id is not None
    assert result.record.user_id == user.id
    assert result.record.workflow_run_id == workflow_run_id
    assert result.record.chat_session_id == chat_session_id
    assert result.record.conversation_id == conversation_id
    assert result.record.review_plan_id == review_plan_id
    assert result.record.source_objective_version == 3
    assert result.record.decision == "approved"
    assert result.record.status == "prepared"
    assert result.record.operation_count == 1

    events = await _events_for(
        user_id=user.id,
        review_plan_id=review_plan_id,
    )

    assert len(events) == 1
    assert events[0].id == result.event_id
    assert events[0].payload["outcome_id"] == str(
        result.record.id
    )
    assert events[0].meta["workflow_run_id"] == str(
        workflow_run_id
    )


@pytest.mark.asyncio
async def test_identical_retry_returns_existing_without_second_event():
    user = _user("support-outcome-retry")
    chat_session_id, _ = await _create_linked_chat_session(
        user
    )
    review_plan_id = str(uuid4())
    outcome = _approved_outcome(
        review_plan_id=review_plan_id
    )

    async with SessionLocal() as db:
        service = CustomerSupportOutcomeRecordingService(db)

        first = await service.record(
            user_id=user.id,
            workflow_run_id=uuid4(),
            chat_session_id=chat_session_id,
            outcome=outcome,
            source_objective_version=1,
            recording_idempotency_key=(
                f"record:{review_plan_id}"
            ),
        )

        second = await service.record(
            user_id=user.id,
            workflow_run_id=uuid4(),
            chat_session_id=chat_session_id,
            outcome=outcome,
            source_objective_version=1,
            recording_idempotency_key=(
                f"record:{review_plan_id}"
            ),
        )

    assert first.created is True
    assert second.created is False
    assert second.record.id == first.record.id
    assert second.event_id is None

    events = await _events_for(
        user_id=user.id,
        review_plan_id=review_plan_id,
    )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_conflicting_retry_raises_domain_conflict():
    user = _user("support-outcome-conflict")
    chat_session_id, _ = await _create_linked_chat_session(
        user
    )
    review_plan_id = str(uuid4())

    async with SessionLocal() as db:
        service = CustomerSupportOutcomeRecordingService(db)

        await service.record(
            user_id=user.id,
            workflow_run_id=uuid4(),
            chat_session_id=chat_session_id,
            outcome=_approved_outcome(
                review_plan_id=review_plan_id,
                message="Original canonical message.",
            ),
            source_objective_version=1,
        )

        with pytest.raises(
            CustomerSupportOutcomeConflictError
        ):
            await service.record(
                user_id=user.id,
                workflow_run_id=uuid4(),
                chat_session_id=chat_session_id,
                outcome=_approved_outcome(
                    review_plan_id=review_plan_id,
                    message="Conflicting canonical message.",
                ),
                source_objective_version=1,
            )

    events = await _events_for(
        user_id=user.id,
        review_plan_id=review_plan_id,
    )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_same_review_plan_identity_is_isolated_by_user():
    first_user = _user("support-outcome-user-one")
    second_user = _user("support-outcome-user-two")

    first_session_id, _ = (
        await _create_linked_chat_session(first_user)
    )
    second_session_id, _ = (
        await _create_linked_chat_session(second_user)
    )

    review_plan_id = str(uuid4())
    outcome = _approved_outcome(
        review_plan_id=review_plan_id
    )

    async with SessionLocal() as first_db:
        first = await CustomerSupportOutcomeRecordingService(
            first_db
        ).record(
            user_id=first_user.id,
            workflow_run_id=uuid4(),
            chat_session_id=first_session_id,
            outcome=outcome,
            source_objective_version=1,
        )

    async with SessionLocal() as second_db:
        second = await CustomerSupportOutcomeRecordingService(
            second_db
        ).record(
            user_id=second_user.id,
            workflow_run_id=uuid4(),
            chat_session_id=second_session_id,
            outcome=outcome,
            source_objective_version=1,
        )

    assert first.created is True
    assert second.created is True
    assert first.record.id != second.record.id
    assert first.record.user_id == first_user.id
    assert second.record.user_id == second_user.id


@pytest.mark.asyncio
async def test_chat_session_ownership_mismatch_is_rejected():
    owner = _user("support-outcome-owner")
    other_user = _user("support-outcome-other")
    chat_session_id, _ = await _create_linked_chat_session(
        owner
    )
    review_plan_id = str(uuid4())

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match="chat session ownership mismatch",
        ):
            await CustomerSupportOutcomeRecordingService(
                db
            ).record(
                user_id=other_user.id,
                workflow_run_id=uuid4(),
                chat_session_id=chat_session_id,
                outcome=_approved_outcome(
                    review_plan_id=review_plan_id
                ),
                source_objective_version=1,
            )

    events = await _events_for(
        user_id=other_user.id,
        review_plan_id=review_plan_id,
    )
    assert events == []


@pytest.mark.asyncio
async def test_missing_inbox_bridge_is_rejected():
    user = _user("support-outcome-no-bridge")
    review_plan_id = str(uuid4())

    async with SessionLocal() as db:
        session = await ChatRepository(db).create_session(
            user_id=user.id,
            visitor_id=f"visitor-{uuid4()}",
            channel="website",
        )
        chat_session_id = session.id
        await db.commit()

    async with SessionLocal() as db:
        with pytest.raises(
            ValueError,
            match="inbox bridge is required",
        ):
            await CustomerSupportOutcomeRecordingService(
                db
            ).record(
                user_id=user.id,
                workflow_run_id=uuid4(),
                chat_session_id=chat_session_id,
                outcome=_approved_outcome(
                    review_plan_id=review_plan_id
                ),
                source_objective_version=1,
            )


@pytest.mark.asyncio
async def test_event_failure_rolls_back_outcome(
    monkeypatch,
):
    user = _user("support-outcome-rollback")
    chat_session_id, _ = await _create_linked_chat_session(
        user
    )
    review_plan_id = str(uuid4())

    async def fail_publish(self, **kwargs):
        raise RuntimeError("forced event failure")

    monkeypatch.setattr(
        PlatformEventPublisher,
        "publish",
        fail_publish,
    )

    async with SessionLocal() as db:
        with pytest.raises(
            RuntimeError,
            match="forced event failure",
        ):
            await CustomerSupportOutcomeRecordingService(
                db
            ).record(
                user_id=user.id,
                workflow_run_id=uuid4(),
                chat_session_id=chat_session_id,
                outcome=_approved_outcome(
                    review_plan_id=review_plan_id
                ),
                source_objective_version=1,
            )

        await db.rollback()

    async with SessionLocal() as db:
        record = (
            await db.execute(
                select(
                    CustomerSupportOutcomeRecord
                ).where(
                    CustomerSupportOutcomeRecord.user_id
                    == user.id,
                    CustomerSupportOutcomeRecord.review_plan_id
                    == review_plan_id,
                )
            )
        ).scalar_one_or_none()

    assert record is None

    events = await _events_for(
        user_id=user.id,
        review_plan_id=review_plan_id,
    )
    assert events == []


@pytest.mark.asyncio
async def test_concurrent_identical_recordings_converge():
    user = _user("support-outcome-concurrent")
    chat_session_id, _ = await _create_linked_chat_session(
        user
    )
    review_plan_id = str(uuid4())
    outcome = _approved_outcome(
        review_plan_id=review_plan_id
    )

    async def record_once():
        async with SessionLocal() as db:
            return await (
                CustomerSupportOutcomeRecordingService(
                    db
                ).record(
                    user_id=user.id,
                    workflow_run_id=uuid4(),
                    chat_session_id=chat_session_id,
                    outcome=outcome,
                    source_objective_version=1,
                    recording_idempotency_key=(
                        f"record:{review_plan_id}"
                    ),
                )
            )

    first, second = await asyncio.gather(
        record_once(),
        record_once(),
    )

    assert sorted(
        [first.created, second.created]
    ) == [False, True]
    assert first.record.id == second.record.id

    events = await _events_for(
        user_id=user.id,
        review_plan_id=review_plan_id,
    )
    assert len(events) == 1
