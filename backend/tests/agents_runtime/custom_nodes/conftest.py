from __future__ import annotations

# PHASE-C TEST AGENT TOOL REGISTRY
import pytest

from tests.agents_runtime.support import (
    build_test_tool_registry,
)


@pytest.fixture
def install_test_agent_tools(monkeypatch):
    """
    Replace only the agent.custom tool-composition seam for tests
    that explicitly exercise synthetic dangerous tools.
    """

    monkeypatch.setattr(
        "app.runtime.nodes.builtins.agent_custom."
        "build_builtin_tool_registry",
        build_test_tool_registry,
    )
