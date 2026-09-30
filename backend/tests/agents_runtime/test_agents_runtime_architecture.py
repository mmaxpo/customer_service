from __future__ import annotations

import ast
from pathlib import Path


_DEAD_PACKAGES = {
    "evaluation",
    "guardrails",
    "memory",
    "patterns",
    "planning",
}


def test_agents_runtime_has_no_dead_placeholder_packages():
    root = Path("app/agents_runtime")

    for name in _DEAD_PACKAGES:
        assert not (root / name).exists()


def test_agents_runtime_has_no_semantically_empty_python_modules():
    root = Path("app/agents_runtime")

    empty = []

    for path in root.rglob("*.py"):
        tree = ast.parse(
            path.read_text(
                encoding="utf-8"
            )
        )

        meaningful = [
            node
            for node in tree.body
            if not (
                isinstance(node, ast.Expr)
                and isinstance(
                    node.value,
                    ast.Constant,
                )
                and isinstance(
                    node.value.value,
                    str,
                )
            )
        ]

        if not meaningful:
            empty.append(str(path))

    assert empty == []


def test_agents_runtime_remains_product_and_runtime_neutral():
    root = Path("app/agents_runtime")

    forbidden = (
        "app.domains.",
        "app.tcos.",
        "app.runtime.",
        "app.providers.",
    )

    violations = []

    for path in root.rglob("*.py"):
        tree = ast.parse(
            path.read_text(
                encoding="utf-8"
            )
        )

        for node in ast.walk(tree):
            modules = []

            if isinstance(
                node,
                ast.ImportFrom,
            ):
                modules.append(
                    node.module or ""
                )

            elif isinstance(
                node,
                ast.Import,
            ):
                modules.extend(
                    alias.name
                    for alias in node.names
                )

            for module in modules:
                if module.startswith(forbidden):
                    violations.append(
                        (
                            str(path),
                            node.lineno,
                            module,
                        )
                    )

    assert violations == []


def test_production_agent_registry_contains_no_test_tools():
    from app.agents_runtime.tools import (
        build_builtin_tool_registry,
    )

    names = {
        tool.name
        for tool in build_builtin_tool_registry().list()
    }

    assert "echo" not in names
    assert "fake_refund_order" not in names
    assert "fake_order_lookup" not in names
    assert "dangerous_test_action" not in names
    assert all(
        not name.startswith("fake_")
        for name in names
    )


def test_test_only_agent_registry_is_owned_under_tests():
    from tests.agents_runtime.support import (
        build_test_tool_registry,
    )

    registry = build_test_tool_registry()

    assert registry.get("echo").risk_level == "safe"

    dangerous = registry.get(
        "dangerous_test_action"
    )

    assert dangerous.risk_level == "dangerous"
    assert dangerous.requires_approval is True
