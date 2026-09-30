from __future__ import annotations

from pydantic import BaseModel


class RateMetric(BaseModel):
    numerator: int
    denominator: int
    rate: float | None


class BusinessValueAnalyticsRead(BaseModel):
    period_days: int
    conversations: int
    resolved_conversations: int
    automation_containment: RateMetric
    first_contact_resolution: RateMetric
    approval_waiting_seconds_average: float | None
    cost_per_resolved_conversation_usd: float | None
    ai_acceptance: RateMetric
    ai_accepted_without_edit: int
    ai_accepted_with_edit: int
    revenue_protected: float
    refunds_prevented: int
    refunds_prevented_amount: float
    provider_failure: RateMetric
    csat_by_intent: dict[str, dict]
    csat_by_workflow: dict[str, dict]
