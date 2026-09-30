from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.platform.jobs.contracts import JobContext

JobHandler = Callable[
    ...,
    Awaitable[dict[str, Any] | None],
]


class JobHandlerRegistry:
    def __init__(self):
        self._handlers: dict[
            str,
            JobHandler,
        ] = {}

    def register(
        self,
        job_type: str,
        handler: JobHandler,
    ) -> None:
        if not job_type or not job_type.strip():
            raise ValueError("job_type is required")

        self._handlers[job_type] = handler

    def get(
        self,
        job_type: str,
    ) -> JobHandler | None:
        return self._handlers.get(job_type)

    def job_types(
        self,
    ) -> set[str]:
        return set(self._handlers.keys())


async def echo_job_handler(
    payload: dict[str, Any],
    ctx: JobContext | None = None,
) -> dict[str, Any]:
    return {
        "echo": payload,
    }


def register_core_job_handlers(
    registry: JobHandlerRegistry,
) -> None:
    registry.register(
        "test.echo",
        echo_job_handler,
    )


default_job_registry = JobHandlerRegistry()

# Compatibility/default application composition.
#
# Generic registry mechanics remain here. Which Tajeran handlers
# participate is decided in app.platform.composition.


__all__ = [
    "JobHandler",
    "JobHandlerRegistry",
    "default_job_registry",
    "echo_job_handler",
    "register_core_job_handlers",
]
