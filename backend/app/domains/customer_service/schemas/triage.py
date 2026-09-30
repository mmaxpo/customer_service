from enum import Enum

from pydantic import BaseModel


class TriagePriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TriageRequest(BaseModel):
    message: str


class TriageResult(BaseModel):
    intent: str

    sentiment: str

    priority: TriagePriority

    confidence: float

    tags: list[str]
