import ast
from pathlib import Path


CHANNELS_API = Path("app/api/products/customer_service/channels.py")


def test_channels_http_has_no_direct_transaction_implementation():
    text = CHANNELS_API.read_text()

    forbidden = (
        "db.commit(",
        "db.execute(",
        "db.flush(",
        "db.add(",
        "session.commit(",
        "session.execute(",
        "pg_advisory_xact_lock",
        "hashtextextended(",
    )

    violations = [marker for marker in forbidden if marker in text]

    assert not violations, (
        "channels HTTP adapter contains direct "
        "transaction/persistence implementation: "
        f"{violations}"
    )


def test_channels_http_does_not_import_sql_expression_primitives():
    tree = ast.parse(CHANNELS_API.read_text())

    violations = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            ast.ImportFrom,
        ):
            continue

        if node.module != "sqlalchemy":
            continue

        violations.extend(alias.name for alias in node.names)

    assert not violations, (
        f"channels HTTP adapter must not import SQL expression primitives: {violations}"
    )


def test_channels_http_delegates_transaction_completion():
    text = CHANNELS_API.read_text()

    assert "await service.commit()" in text

    assert "acquire_public_ingress_lock(" in text
