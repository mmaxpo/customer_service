from __future__ import annotations

from pydantic import BaseModel


class AIReplyRegenerateRead(BaseModel):
    body: str
    confidence: float
    generation: int
    regenerated: bool
    sources: dict
