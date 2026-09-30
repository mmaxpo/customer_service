from __future__ import annotations

from collections import Counter

from app.domains.customer_service.repositories.analytics import (
    AnalyticsRepository,
)


class RoutingAssigneeSelector:
    def __init__(self, analytics_repo: AnalyticsRepository):
        self.analytics_repo = analytics_repo

    async def select(
        self,
        *,
        user_id,
        strategy: str,
        candidate_assignee_ids: list[str],
        max_open_tickets_by_assignee: dict[str, int] | None = None,
    ) -> str | None:

        if not candidate_assignee_ids:
            return None

        workload_rows = await self.analytics_repo.workload_by_assignee(
            user_id,
        )

        load_by_assignee = Counter(
            {
                str(row["assigned_to"]): int(row["open_or_pending_tickets"])
                for row in workload_rows
            }
        )

        max_open_tickets_by_assignee = max_open_tickets_by_assignee or {}

        eligible_candidates = [
            assignee_id
            for assignee_id in candidate_assignee_ids
            if load_by_assignee.get(assignee_id, 0)
            < max_open_tickets_by_assignee.get(assignee_id, 10**9)
        ]

        if not eligible_candidates:
            return None

        if strategy == "first_available":
            return eligible_candidates[0]

        return min(
            eligible_candidates,
            key=lambda assignee_id: (
                load_by_assignee.get(assignee_id, 0),
                assignee_id,
            ),
        )
