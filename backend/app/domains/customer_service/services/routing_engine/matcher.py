from __future__ import annotations

from app.domains.customer_service.models import (
    CustomerServiceRoutingPolicy,
)


class RoutingPolicyMatcher:
    @staticmethod
    def matches(
        *,
        policy: CustomerServiceRoutingPolicy,
        channel: str | None,
        intent: str | None,
        priority: str | None,
        body: str | None = None,
    ) -> bool:

        if policy.channel and policy.channel != channel:
            return False

        if policy.intent and policy.intent != intent:
            return False

        if policy.priority and policy.priority != priority:
            return False

        filters = policy.filters or {}

        keywords = filters.get("keywords") or []

        if keywords and body:
            lower = body.lower()

            if not any(keyword.lower() in lower for keyword in keywords):
                return False

        return True
