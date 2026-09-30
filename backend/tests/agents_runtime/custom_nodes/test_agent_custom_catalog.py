from app.runtime.nodes.registry.builtins import register_builtin_nodes
from app.runtime.nodes.registry import list_registered_nodes


def test_agent_custom_is_in_catalog():
    register_builtin_nodes()

    nodes = list_registered_nodes()
    agent_custom = next(node for node in nodes if node["node_type"] == "agent.custom")

    assert agent_custom["title"] == "Custom Agent"
    assert agent_custom["category"] == "agent"
    assert agent_custom["default_config"]["backend"] == "pure"
    assert agent_custom["default_config"]["pattern"] == "tool_agent"
    assert agent_custom["schema"]["title"] == "AgentCustomConfig"
