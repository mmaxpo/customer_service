from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.tcos.compiler.diagnostics import CompilerDiagnostic
from app.tcos.compiler.execution_ir.models import ExecutionGraph


class CompilationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    execution_graph: ExecutionGraph | None = None
    diagnostics: list[CompilerDiagnostic] = Field(default_factory=list)
