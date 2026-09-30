from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PlatformJob
from app.workflow_operations.snapshots.json_safe import make_json_safe


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def enqueue(
        self,
        *,
        job_type: str,
        payload: dict,
        user_id=None,
        max_attempts: int = 3,
        run_after: datetime | None = None,
        idempotency_key: str | None = None,
        commit: bool = True,
    ) -> PlatformJob:
        normalized_key = (
            str(idempotency_key).strip() if idempotency_key is not None else None
        )

        if normalized_key == "":
            normalized_key = None

        values = {
            "user_id": user_id,
            "job_type": job_type,
            "idempotency_key": normalized_key,
            "payload": payload or {},
            "max_attempts": max_attempts,
            "run_after": (run_after or datetime.now(timezone.utc)),
            "status": "queued",
        }

        if normalized_key is None:
            job = PlatformJob(**values)
            self.db.add(job)

            if commit:
                await self.db.commit()
                await self.db.refresh(job)
            else:
                await self.db.flush()

            return job

        if user_id is None:
            conflict_elements = [
                PlatformJob.job_type,
                PlatformJob.idempotency_key,
            ]
            conflict_where = and_(
                PlatformJob.idempotency_key.is_not(None),
                PlatformJob.user_id.is_(None),
            )
        else:
            conflict_elements = [
                PlatformJob.user_id,
                PlatformJob.job_type,
                PlatformJob.idempotency_key,
            ]
            conflict_where = and_(
                PlatformJob.idempotency_key.is_not(None),
                PlatformJob.user_id.is_not(None),
            )

        stmt = (
            insert(PlatformJob)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=conflict_elements,
                index_where=conflict_where,
            )
            .returning(PlatformJob.id)
        )

        result = await self.db.execute(stmt)
        inserted_id = result.scalar_one_or_none()

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        if inserted_id is not None:
            job = await self.get(inserted_id)

            if job is None:
                raise RuntimeError("Inserted platform job could not be read")

            return job

        ownership_clause = (
            PlatformJob.user_id.is_(None)
            if user_id is None
            else PlatformJob.user_id == user_id
        )

        existing_result = await self.db.execute(
            select(PlatformJob).where(
                ownership_clause,
                PlatformJob.job_type == job_type,
                PlatformJob.idempotency_key == normalized_key,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is None:
            raise RuntimeError(
                "Idempotent platform job conflict occurred without an existing job"
            )

        return existing

    async def get(self, job_id: UUID) -> PlatformJob | None:
        result = await self.db.execute(
            select(PlatformJob).where(PlatformJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        *,
        job_id: UUID,
        user_id,
    ) -> PlatformJob | None:
        result = await self.db.execute(
            select(PlatformJob).where(
                PlatformJob.id == job_id,
                PlatformJob.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, *, user_id, limit: int = 50) -> list[PlatformJob]:
        result = await self.db.execute(
            select(PlatformJob)
            .where(PlatformJob.user_id == user_id)
            .order_by(PlatformJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def claim_next_due(
        self,
        *,
        worker_id: str,
        job_types: set[str] | None = None,
        job_id=None,
    ) -> PlatformJob | None:
        now = datetime.now(timezone.utc)

        stmt = (
            select(PlatformJob)
            .where(
                PlatformJob.status == "queued",
                PlatformJob.run_after <= now,
                PlatformJob.attempts < PlatformJob.max_attempts,
            )
            .order_by(PlatformJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        if job_types:
            stmt = stmt.where(PlatformJob.job_type.in_(job_types))

        if job_id is not None:
            stmt = stmt.where(PlatformJob.id == job_id)

        result = await self.db.execute(stmt)

        job = result.scalar_one_or_none()

        if job is None:
            return None

        job.status = "running"
        job.locked_by = worker_id
        job.locked_at = now
        job.heartbeat_at = now
        job.started_at = now
        job.attempts += 1

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_succeeded(
        self,
        *,
        job: PlatformJob,
        result: dict | None = None,
    ) -> PlatformJob:
        now = datetime.now(timezone.utc)

        job.status = "succeeded"
        job.result = make_json_safe(result or {})
        job.error_message = None
        job.finished_at = now
        job.locked_at = None
        job.locked_by = None
        job.heartbeat_at = None

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def mark_failed(
        self,
        *,
        job_id: UUID,
        error_message: str,
        run_after: datetime | None,
    ) -> PlatformJob:
        job = await self.get(job_id)

        if job is None:
            raise RuntimeError(
                f"Platform job disappeared during failure handling: {job_id}"
            )

        now = datetime.now(timezone.utc)

        if job.attempts >= job.max_attempts:
            job.status = "dead_letter"
            job.finished_at = now
        else:
            job.status = "queued"
            job.run_after = run_after or now

        job.error_message = error_message
        job.locked_at = None
        job.locked_by = None
        job.heartbeat_at = None

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def heartbeat(self, *, job: PlatformJob, worker_id: str) -> PlatformJob:
        if job.locked_by != worker_id:
            raise RuntimeError("Cannot heartbeat job locked by another worker")

        job.heartbeat_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)
        return job
