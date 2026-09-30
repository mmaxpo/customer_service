from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LlmResult:
    text: str
    model: str | None = None
    usage: dict | None = None
