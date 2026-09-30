import pytest

from app.domains.customer_service.services.routing_engine.selector import (
    RoutingAssigneeSelector,
)


class FakeAnalyticsRepo:
    def __init__(self, rows):
        self.rows = rows

    async def workload_by_assignee(self, user_id):
        return self.rows


@pytest.mark.asyncio
async def test_selector_skips_agent_at_capacity():

    selector = RoutingAssigneeSelector(
        FakeAnalyticsRepo(
            [
                {
                    "assigned_to": "agent-a",
                    "open_or_pending_tickets": 10,
                },
                {
                    "assigned_to": "agent-b",
                    "open_or_pending_tickets": 3,
                },
            ]
        )
    )

    selected = await selector.select(
        user_id="u1",
        strategy="least_loaded",
        candidate_assignee_ids=[
            "agent-a",
            "agent-b",
        ],
        max_open_tickets_by_assignee={
            "agent-a": 10,
            "agent-b": 10,
        },
    )

    assert selected == "agent-b"


@pytest.mark.asyncio
async def test_selector_returns_none_when_all_agents_full():

    selector = RoutingAssigneeSelector(
        FakeAnalyticsRepo(
            [
                {
                    "assigned_to": "agent-a",
                    "open_or_pending_tickets": 10,
                },
                {
                    "assigned_to": "agent-b",
                    "open_or_pending_tickets": 10,
                },
            ]
        )
    )

    selected = await selector.select(
        user_id="u1",
        strategy="least_loaded",
        candidate_assignee_ids=[
            "agent-a",
            "agent-b",
        ],
        max_open_tickets_by_assignee={
            "agent-a": 10,
            "agent-b": 10,
        },
    )

    assert selected is None
