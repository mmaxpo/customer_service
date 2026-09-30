from __future__ import annotations

from app.tcos.planner.runtime.models import (
    PlannerSession,
    PlanningStatus,
)

__all__ = [
    "PlanGenerationResult",
    "PlannerRuntime",
    "PlannerSession",
    "PlanningStatus",
]


def __getattr__(name: str):
    if name == "PlanGenerationResult":
        from app.tcos.planner.runtime.plan_generation_result import (
            PlanGenerationResult,
        )

        return PlanGenerationResult

    if name == "PlannerRuntime":
        from app.tcos.planner.runtime.engine import (
            PlannerRuntime,
        )

        return PlannerRuntime

    raise AttributeError(name)
