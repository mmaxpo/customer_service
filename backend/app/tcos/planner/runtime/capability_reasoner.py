from __future__ import annotations

import re

_URL_RE = re.compile(r"https?://[^\s]+")
from pydantic import BaseModel, ConfigDict, Field

from app.tcos.planner.runtime.intent import PlannerIntent
from app.tcos.planner.runtime.planning_context import PlanningContext


class CapabilityReasoningResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_name: str
    entities: dict = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    selected_capability: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""


class CapabilityReasoner:
    def reason(
        self,
        *,
        intent: PlannerIntent,
        context: PlanningContext | None = None,
    ) -> CapabilityReasoningResult:
        text = (context.user_message if context else "") or ""
        normalized = text.lower()

        if _URL_RE.search(text) and any(
            word in normalized
            for word in ["summarize", "summary", "read", "extract", "explain"]
        ):
            return CapabilityReasoningResult(
                intent_name=intent.name,
                entities={},
                selected_capability="generic.url_summary",
                required_capabilities=[
                    "runtime.web_fetch_extract",
                    "runtime.llm_generate",
                    "runtime.response",
                ],
                confidence=0.92,
                reasoning="Goal contains a URL and asks for summary/extraction.",
            )



        return CapabilityReasoningResult(
            intent_name=intent.name,
            entities={},
            selected_capability="unknown",
            required_capabilities=[],
            confidence=0.0,
            reasoning=f"No capability reasoning path for intent {intent.name}.",
        )
