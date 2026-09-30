from app.tcos.capabilities.planner import CapabilityMatchRequest, match_capabilities


def test_match_capabilities_returns_ranked_matches():
    response = match_capabilities(CapabilityMatchRequest(query="knowledge"))

    assert response.query == "knowledge"
    assert response.matches
    assert response.matches[0].score >= response.matches[-1].score
    assert any(
        match.capability.id == "agent_tool.knowledge_search"
        for match in response.matches
    )


def test_match_capabilities_respects_required_inputs():
    response = match_capabilities(
        CapabilityMatchRequest(
            query="calculator",
            required_inputs=["expression"],
        )
    )

    assert any(
        match.capability.id == "agent_tool.calculator" for match in response.matches
    )


def test_match_capabilities_filters_incompatible_inputs():
    response = match_capabilities(
        CapabilityMatchRequest(
            query="calculator",
            required_inputs=["order_id"],
        )
    )

    assert all(
        match.capability.id != "agent_tool.calculator" for match in response.matches
    )
