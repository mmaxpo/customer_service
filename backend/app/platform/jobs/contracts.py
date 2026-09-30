from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.models import PlatformJob


@dataclass
class JobContext:
    """Execution context passed to one platform job handler."""

    db: Any
    job: PlatformJob
    worker_id: str
    retryable: bool = True


__all__ = [
    "JobContext",
]
