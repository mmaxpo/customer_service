from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CompilerDiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class CompilerDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: CompilerDiagnosticSeverity
    code: str
    message: str
    location: str | None = None
    details: dict = Field(default_factory=dict)
