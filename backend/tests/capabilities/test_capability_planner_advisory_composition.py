from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.tcos.capabilities.planner import (
    CapabilityMatchRequest,
    match_capabilities,
)
from app.tcos.capabilities.planner_advisory_composition import (
    CapabilityAdvisoryMatchRequest,
    CapabilityPlannerAdvisoryComposer,
)


class FakeAdvisoryService:
    def __init__(self):
        self.calls = []

    async def list_for_scope(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)
        return []


@pytest.mark.asyncio
async def test_composition_preserves_scores_and_order():
    user_id = uuid4()
    service = FakeAdvisoryService()

    request = CapabilityAdvisoryMatchRequest(
        query="knowledge",
        limit=10,
        tenant_id="tenant-a",
        provider_id="builtin",
        provider_ref=None,
        action="search",
    )

    base = match_capabilities(
        CapabilityMatchRequest(
            query=request.query,
            limit=request.limit,
        )
    )

    composed = await (
        CapabilityPlannerAdvisoryComposer(
            db=SimpleNamespace(),
            advisory_service=service,
        )
        .compose(
            user_id=user_id,
            request=request,
        )
    )

    assert [
        item.capability.id
        for item in composed.matches
    ] == [
        item.capability.id
        for item in base.matches
    ]

    assert [
        item.score
        for item in composed.matches
    ] == [
        item.score
        for item in base.matches
    ]

    assert composed.query == base.query
    assert (
        composed.ranking_affected_by_advisories
        is False
    )

    assert len(service.calls) == len(
        base.matches
    )

    assert all(
        call["user_id"] == user_id
        for call in service.calls
    )
    assert all(
        call["tenant_id"] == "tenant-a"
        for call in service.calls
    )
    assert all(
        call["provider_id"] == "builtin"
        for call in service.calls
    )
    assert all(
        call["action"] == "search"
        for call in service.calls
    )


@pytest.mark.asyncio
async def test_composition_passes_each_capability_scope():
    service = FakeAdvisoryService()

    response = await (
        CapabilityPlannerAdvisoryComposer(
            db=SimpleNamespace(),
            advisory_service=service,
        )
        .compose(
            user_id=uuid4(),
            request=(
                CapabilityAdvisoryMatchRequest(
                    query="calculator",
                    required_inputs=[
                        "expression"
                    ],
                )
            ),
        )
    )

    assert response.matches

    expected_ids = {
        item.capability.id
        for item in response.matches
    }
    requested_ids = {
        call["capability_id"]
        for call in service.calls
    }

    assert requested_ids == expected_ids


@pytest.mark.asyncio
async def test_composition_keeps_empty_advisories_explicit():
    response = await (
        CapabilityPlannerAdvisoryComposer(
            db=SimpleNamespace(),
            advisory_service=(
                FakeAdvisoryService()
            ),
        )
        .compose(
            user_id=uuid4(),
            request=(
                CapabilityAdvisoryMatchRequest(
                    query="knowledge",
                    limit=3,
                )
            ),
        )
    )

    assert response.matches
    assert all(
        item.advisories == []
        for item in response.matches
    )
    assert all(
        item.advisory_context.advisory_count
        == 0
        for item in response.matches
    )
    assert all(
        item.advisory_context
        .affects_ranking
        is False
        for item in response.matches
    )
    assert all(
        item.rendered_advisory_context
        .present
        is False
        for item in response.matches
    )
    assert all(
        item.rendered_advisory_context
        .text
        == ""
        for item in response.matches
    )
