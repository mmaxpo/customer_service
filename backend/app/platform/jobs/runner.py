from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.session import SessionLocal
from app.core.observability import initialize_observability
from app.core.startup_validation import validate_startup_configuration
from app.platform.jobs.recovery import JobRecoveryService
from app.platform.jobs.worker import JobWorker
from app.platform.schedules.scheduler import WorkflowScheduler
from app.runtime.capabilities.execution.health.maintenance import (
    CapabilityHealthMaintenanceTicker,
)

logger = logging.getLogger(__name__)


class JobWorkerRunner:
    def __init__(
        self,
        *,
        worker_id: str | None = None,
        idle_sleep_seconds: float = 1.0,
        busy_sleep_seconds: float = 0.05,
        recovery_interval_seconds: float = 30.0,
        schedule_tick_interval_seconds: float = 1.0,
        health_maintenance_enabled: bool | None = None,
        health_maintenance_check_interval_seconds: (float | None) = None,
        health_window_hours: int | None = None,
        health_lookback_windows: int | None = None,
        health_scope_limit: int | None = None,
    ):
        self.worker_id = worker_id or f"{socket.gethostname()}-{uuid.uuid4()}"
        self.idle_sleep_seconds = idle_sleep_seconds
        self.busy_sleep_seconds = busy_sleep_seconds
        self.recovery_interval_seconds = recovery_interval_seconds
        self.schedule_tick_interval_seconds = float(schedule_tick_interval_seconds)

        self.health_maintenance_enabled = (
            bool(settings.CAPABILITY_HEALTH_MAINTENANCE_ENABLED)
            if health_maintenance_enabled is None
            else bool(health_maintenance_enabled)
        )
        self.health_maintenance_check_interval_seconds = (
            float(settings.CAPABILITY_HEALTH_MAINTENANCE_CHECK_INTERVAL_SECONDS)
            if (health_maintenance_check_interval_seconds is None)
            else float(health_maintenance_check_interval_seconds)
        )
        self.health_window_hours = (
            int(settings.CAPABILITY_HEALTH_WINDOW_HOURS)
            if health_window_hours is None
            else int(health_window_hours)
        )
        self.health_lookback_windows = (
            int(settings.CAPABILITY_HEALTH_LOOKBACK_WINDOWS)
            if health_lookback_windows is None
            else int(health_lookback_windows)
        )
        self.health_scope_limit = (
            int(settings.CAPABILITY_HEALTH_SCOPE_LIMIT)
            if health_scope_limit is None
            else int(health_scope_limit)
        )

        if self.schedule_tick_interval_seconds <= 0:
            raise ValueError("schedule tick interval must be > 0")
        if self.health_maintenance_check_interval_seconds <= 0:
            raise ValueError("health maintenance check interval must be > 0")
        if self.health_window_hours < 1:
            raise ValueError("health_window_hours must be >= 1")
        if self.health_lookback_windows < 1:
            raise ValueError("health_lookback_windows must be >= 1")
        if self.health_scope_limit < 1:
            raise ValueError("health_scope_limit must be >= 1")

        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        logger.info("job worker runner started worker_id=%s", self.worker_id)
        self._touch_healthcheck()
        last_recovery_at = 0.0
        last_schedule_tick_at = 0.0
        last_health_maintenance_at = 0.0

        while not self._stop.is_set():
            now = asyncio.get_running_loop().time()

            try:
                async with SessionLocal() as db:
                    if now - last_recovery_at >= self.recovery_interval_seconds:
                        await JobRecoveryService(db).recover_abandoned()
                        last_recovery_at = now

                    if (
                        now - last_schedule_tick_at
                        >= self.schedule_tick_interval_seconds
                    ):
                        # Record the attempt before execution so a broken
                        # scheduler cannot create a tight retry loop.
                        last_schedule_tick_at = now

                        try:
                            result = await WorkflowScheduler(db).tick()
                            logger.debug(
                                "workflow schedule tick completed result=%s",
                                result,
                            )
                        except asyncio.CancelledError:
                            raise
                        except Exception:
                            logger.exception("workflow schedule tick failed")
                            await db.rollback()

                    if self.health_maintenance_enabled and (
                        now - last_health_maintenance_at
                        >= self.health_maintenance_check_interval_seconds
                    ):
                        # Record the attempt time even when enqueueing fails so
                        # a broken maintenance dependency cannot create a tight
                        # retry/logging loop or block normal job processing.
                        last_health_maintenance_at = now

                        try:
                            result = await CapabilityHealthMaintenanceTicker(
                                db,
                                window_hours=(self.health_window_hours),
                                lookback_windows=(self.health_lookback_windows),
                                scope_limit=(self.health_scope_limit),
                            ).tick()
                            logger.debug(
                                "capability health maintenance "
                                "tick completed result=%s",
                                result,
                            )
                        except asyncio.CancelledError:
                            raise
                        except Exception:
                            logger.exception(
                                "capability health maintenance tick failed"
                            )
                            await db.rollback()

                    processed = await JobWorker(
                        db,
                        worker_id=self.worker_id,
                    ).run_once()

                    await db.commit()

                self._touch_healthcheck()

                await asyncio.sleep(
                    self.busy_sleep_seconds
                    if processed is not None
                    else self.idle_sleep_seconds
                )

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("job worker runner loop failed")
                await asyncio.sleep(self.idle_sleep_seconds)

        logger.info("job worker runner stopped worker_id=%s", self.worker_id)

    @staticmethod
    def _touch_healthcheck() -> None:
        path = Path(settings.WORKER_HEARTBEAT_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


async def run_worker_until_cancelled() -> None:
    runner = JobWorkerRunner()
    try:
        await runner.run_forever()
    finally:
        runner.stop()


def main() -> None:
    initialize_observability()
    validate_startup_configuration(settings)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run_worker_until_cancelled())


if __name__ == "__main__":
    main()
