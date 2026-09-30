from __future__ import annotations

from app.runtime.objectives.cognition import (
    ObjectiveCognitiveContext,
)
from app.tcos.planner.runtime.planning_context import PlanningContext


def build_default_planning_context(
    *,
    user_message: str,
    objective_context: (
        ObjectiveCognitiveContext | None
    ) = None,
) -> PlanningContext:

    return PlanningContext(
        user_message=user_message,
        objective_context=objective_context,
    )
