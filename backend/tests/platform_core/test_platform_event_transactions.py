from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.session import SessionLocal
from app.models.models import PlatformEvent
from app.platform.events.publisher import PlatformEventPublisher


@pytest.mark.asyncio
async def test_platform_event_can_join_caller_transaction():
    user_id = uuid4()
    event_id = None

    async with SessionLocal() as db:
        result = await PlatformEventPublisher(
            db
        ).publish(
            user_id=user_id,
            event_type="test.transactional",
            source="test",
            payload={"value": 1},
            dispatch=False,
            commit=False,
        )

        event_id = result["event"].id

        visible_in_transaction = await db.execute(
            select(PlatformEvent).where(
                PlatformEvent.id == event_id
            )
        )

        assert (
            visible_in_transaction.scalar_one_or_none()
            is not None
        )

        await db.rollback()

    async with SessionLocal() as db:
        persisted = await db.execute(
            select(PlatformEvent).where(
                PlatformEvent.id == event_id
            )
        )

        assert persisted.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_platform_event_default_still_commits():
    user_id = uuid4()

    async with SessionLocal() as db:
        result = await PlatformEventPublisher(
            db
        ).publish(
            user_id=user_id,
            event_type="test.default_commit",
            source="test",
            payload={"value": 1},
            dispatch=False,
        )

        event_id = result["event"].id

    async with SessionLocal() as db:
        persisted = await db.execute(
            select(PlatformEvent).where(
                PlatformEvent.id == event_id
            )
        )

        assert persisted.scalar_one_or_none() is not None
