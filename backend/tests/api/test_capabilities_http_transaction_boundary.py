import ast
from pathlib import Path

CAPABILITIES_API = Path("app/api/capabilities.py")

TARGET_WRITE_ROUTES = {
    "create_capability_runtime_policy_revision",
    "update_provider_installation_enabled",
    "reconcile_shopify_provider_installation",
}

FORBIDDEN_TRANSACTION_MARKERS = (
    "await db.commit()",
    "await db.rollback()",
    "await db.refresh(",
    "await db.flush()",
    "db.add(",
)


def _target_route_sources() -> dict[str, str]:
    text = CAPABILITIES_API.read_text()
    tree = ast.parse(text)

    found = {}

    for node in tree.body:
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node.name not in TARGET_WRITE_ROUTES:
            continue

        source = ast.get_source_segment(
            text,
            node,
        )

        assert source is not None
        found[node.name] = source

    assert set(found) == TARGET_WRITE_ROUTES

    return found


def test_confirmed_capability_write_routes_do_not_complete_transactions_in_http():
    for name, source in _target_route_sources().items():
        violations = [
            marker for marker in FORBIDDEN_TRANSACTION_MARKERS if marker in source
        ]

        assert not violations, (
            f"{name} contains direct HTTP transaction implementation: {violations}"
        )


def test_runtime_policy_route_uses_policy_write_operation():
    source = _target_route_sources()["create_capability_runtime_policy_revision"]

    assert "CapabilityRuntimePolicyOperations(" in source


def test_installation_write_routes_use_installation_operations():
    sources = _target_route_sources()

    assert (
        "CapabilityProviderInstallationOperations("
        in sources["update_provider_installation_enabled"]
    )

    assert (
        "CapabilityProviderInstallationOperations("
        in sources["reconcile_shopify_provider_installation"]
    )


def test_unrelated_capability_routes_are_not_part_of_this_boundary_rule():
    text = CAPABILITIES_API.read_text()

    # E6 is intentionally scoped. Existing rollback handling
    # in unrelated learning/verification HTTP paths is not
    # silently changed by this architecture step.
    assert "await db.rollback()" in text
