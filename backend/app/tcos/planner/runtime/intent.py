from __future__ import annotations

from app.tcos.planner.product_planning.contracts import (
    PlannerIntent,
    PlannerIntentName,
)


def detect_intent(*, text: str) -> PlannerIntent:
    normalized = text.lower()

    customer_reply_terms = [
        "reply",
        "answer",
        "respond",
        "customer",
        "order",
        "refund",
        "replacement",
        "where is my",
        "damaged",
    ]

    hits = sum(
        1
        for term in customer_reply_terms
        if term in normalized
    )

    if hits:
        confidence = min(
            0.95,
            0.55 + hits * 0.1,
        )

        return PlannerIntent(
            name=PlannerIntentName.CUSTOMER_REPLY,
            confidence=confidence,
        )

    return PlannerIntent(
        name=PlannerIntentName.UNKNOWN,
        confidence=0.2,
        needs_clarification=True,
    )


__all__ = [
    "PlannerIntent",
    "PlannerIntentName",
    "detect_intent",
]
