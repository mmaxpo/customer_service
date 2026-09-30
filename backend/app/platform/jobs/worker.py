from __future__ import annotations

import asyncio
import contextlib
import inspect

from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.composition import build_default_job_registry
from app.platform.events.publisher import PlatformEventPublisher
from app.platform.jobs.dead_letter import DeadLetterRepository
from app.platform.jobs.handlers import JobContext, JobHandlerRegistry
from app.platform.jobs.repository import JobRepository
from app.platform.jobs.retry import ExponentialBackoffRetry


class JobWorker:
    def __init__(
        self,
        db: AsyncSession,
        *,
        worker_id: str,
        registry: JobHandlerRegistry | None = None,
        retry_strategy: ExponentialBackoffRetry | None = None,
    ):
        self.db = db
        self.worker_id = worker_id
        self.repo = JobRepository(db)
        self.registry = (
            registry if registry is not None else build_default_job_registry()
        )
        self.retry_strategy = retry_strategy or ExponentialBackoffRetry()

    async def run_once(self, job_id=None):
        job = await self.repo.claim_next_due(
            worker_id=self.worker_id,
            job_types=self.registry.job_types(),
            job_id=job_id,
        )

        if job is None:
            return None

        # Application handlers share this AsyncSession and may rollback it.
        # A rollback expires ORM state, so failure handling must retain only
        # scalar identifiers captured before application code runs.
        job_id = job.id
        job_type = job.job_type
        attempts = job.attempts

        handler = self.registry.get(job_type)

        if handler is None:
            return await self._fail_job(
                job_id=job_id,
                attempts=attempts,
                error_message=f"No handler registered for job type: {job_type}",
            )

        ctx = JobContext(
            db=self.db,
            job=job,
            worker_id=self.worker_id,
        )

        try:
            heartbeat_task = asyncio.create_task(
                self._heartbeat_until_done(job=job, interval_seconds=30)
            )

            try:
                result = await self._call_handler(
                    handler=handler,
                    payload=job.payload or {},
                    ctx=ctx,
                )
            finally:
                heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat_task

        except Exception as exc:
            retryable = ctx.retryable

            # Handler application writes share this session.
            # They must never become durable when execution fails.
            #
            # Retry intent is kept on JobContext rather than ORM
            # state so it survives this rollback.
            await self.db.rollback()

            return await self._fail_job(
                job_id=job_id,
                attempts=attempts,
                error_message=str(exc),
                retryable=retryable,
            )

        saved = await self.repo.mark_succeeded(
            job=job,
            result=result or {},
        )

        await PlatformEventPublisher(self.db).publish(
            user_id=saved.user_id,
            event_type="job.succeeded",
            source="jobs",
            payload={
                "job_id": str(saved.id),
                "job_type": saved.job_type,
                "result": saved.result,
            },
            dispatch=True,
        )

        return saved

    async def _fail_job(
        self,
        *,
        job_id,
        attempts: int,
        error_message: str,
        retryable: bool = True,
    ):
        next_retry_at = self.retry_strategy.next_retry_at(attempts)

        if not retryable:
            job = await self.repo.get(job_id)

            if job is None:
                raise RuntimeError(
                    "Platform job disappeared during "
                    f"terminal failure handling: {job_id}"
                )

            job.max_attempts = attempts
            await self.db.flush()

        saved = await self.repo.mark_failed(
            job_id=job_id,
            error_message=error_message,
            run_after=next_retry_at,
        )

        await PlatformEventPublisher(self.db).publish(
            user_id=saved.user_id,
            event_type="job.failed",
            source="jobs",
            payload={
                "job_id": str(saved.id),
                "job_type": saved.job_type,
                "status": saved.status,
                "attempts": saved.attempts,
                "max_attempts": saved.max_attempts,
                "error_message": error_message,
            },
            dispatch=True,
        )

        if saved.status == "dead_letter":
            dead = await DeadLetterRepository(self.db).create_from_job(
                job=saved,
                error_message=error_message,
            )

            await PlatformEventPublisher(self.db).publish(
                user_id=saved.user_id,
                event_type="job.dead_lettered",
                source="jobs",
                payload={
                    "job_id": str(saved.id),
                    "dead_letter_id": str(dead.id),
                    "job_type": saved.job_type,
                    "attempts": saved.attempts,
                    "error_message": error_message,
                },
                dispatch=True,
            )

        return saved

    async def _call_handler(self, *, handler, payload: dict, ctx: JobContext):
        signature = inspect.signature(handler)

        if len(signature.parameters) >= 2:
            return await handler(payload, ctx)

        return await handler(payload)

    async def _heartbeat_until_done(self, *, job, interval_seconds: float = 30.0):
        while True:
            await asyncio.sleep(interval_seconds)
            await self.repo.heartbeat(job=job, worker_id=self.worker_id)
