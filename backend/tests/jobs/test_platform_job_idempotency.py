from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.session import SessionLocal
from app.models.models import PlatformJob
from app.platform.jobs.repository import JobRepository


@pytest.mark.asyncio
async def test_job_enqueue_reuses_idempotency_key():
    user_id = uuid4()
    key = f"test-idempotency-{uuid4()}"

    async with SessionLocal() as db:
        repo = JobRepository(db)

        first = await repo.enqueue(
            user_id=user_id,
            job_type="test.echo",
            payload={"value": 1},
            idempotency_key=key,
        )

        second = await repo.enqueue(
            user_id=user_id,
            job_type="test.echo",
            payload={"value": 2},
            idempotency_key=key,
        )

        count = await db.scalar(
            select(func.count(PlatformJob.id)).where(
                PlatformJob.job_type == "test.echo",
                PlatformJob.idempotency_key == key,
            )
        )

    assert first.id == second.id
    assert second.payload == {"value": 1}
    assert count == 1


@pytest.mark.asyncio
async def test_same_key_isolated_by_job_type():
    user_id = uuid4()
    key = f"test-type-isolation-{uuid4()}"

    async with SessionLocal() as db:
        repo = JobRepository(db)

        first = await repo.enqueue(
            user_id=user_id,
            job_type="test.echo",
            payload={},
            idempotency_key=key,
        )

        second = await repo.enqueue(
            user_id=user_id,
            job_type="workflow.run",
            payload={},
            idempotency_key=key,
        )

    assert first.id != second.id


@pytest.mark.asyncio
async def test_same_idempotency_key_isolated_by_user():
    user_a = uuid4()
    user_b = uuid4()
    key = f"test-user-isolation-{uuid4()}"
    job_type = f"test.user-isolation.{uuid4()}"

    async with SessionLocal() as db:
        repo = JobRepository(db)

        first_a = await repo.enqueue(
            user_id=user_a,
            job_type=job_type,
            payload={"owner": "a", "request": 1},
            idempotency_key=key,
        )

        second_a = await repo.enqueue(
            user_id=user_a,
            job_type=job_type,
            payload={"owner": "a", "request": 2},
            idempotency_key=key,
        )

        first_b = await repo.enqueue(
            user_id=user_b,
            job_type=job_type,
            payload={"owner": "b", "request": 1},
            idempotency_key=key,
        )

        second_b = await repo.enqueue(
            user_id=user_b,
            job_type=job_type,
            payload={"owner": "b", "request": 2},
            idempotency_key=key,
        )

        rows = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.job_type == job_type,
                        PlatformJob.idempotency_key == key,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert first_a.id == second_a.id
    assert first_b.id == second_b.id

    assert first_a.id != first_b.id

    assert first_a.user_id == user_a
    assert first_b.user_id == user_b

    assert second_a.payload == {
        "owner": "a",
        "request": 1,
    }
    assert second_b.payload == {
        "owner": "b",
        "request": 1,
    }

    assert len(rows) == 2
    assert {row.user_id for row in rows} == {
        user_a,
        user_b,
    }


@pytest.mark.asyncio
async def test_global_job_idempotency_remains_deduplicated():
    key = f"test-global-idempotency-{uuid4()}"
    job_type = f"test.global-idempotency.{uuid4()}"

    async with SessionLocal() as db:
        repo = JobRepository(db)

        first = await repo.enqueue(
            user_id=None,
            job_type=job_type,
            payload={"request": 1},
            idempotency_key=key,
        )

        second = await repo.enqueue(
            user_id=None,
            job_type=job_type,
            payload={"request": 2},
            idempotency_key=key,
        )

        rows = list(
            (
                await db.execute(
                    select(PlatformJob).where(
                        PlatformJob.user_id.is_(None),
                        PlatformJob.job_type == job_type,
                        PlatformJob.idempotency_key == key,
                    )
                )
            )
            .scalars()
            .all()
        )

    assert first.id == second.id
    assert first.user_id is None
    assert second.user_id is None
    assert second.payload == {"request": 1}
    assert len(rows) == 1
