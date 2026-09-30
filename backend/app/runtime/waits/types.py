from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RuntimeWait:
    wait_type: str
    payload: dict[str, Any]
    expires_at: datetime | None = None
