import ast
from pathlib import Path


AUTH_API = Path("app/api/auth.py")


def test_auth_http_adapter_has_no_direct_user_persistence():
    text = AUTH_API.read_text()

    forbidden = (
        "select(",
        "UserORM",
        "session.execute(",
        "session.add(",
        "session.commit(",
        "jwt.decode(",
        "jwt.encode(",
        "pwd_context",
        "CryptContext",
    )

    violations = [marker for marker in forbidden if marker in text]

    assert not violations, (
        "app/api/auth.py must remain "
        "an HTTP adapter; forbidden "
        "identity/persistence ownership: "
        f"{violations}"
    )


def test_auth_http_adapter_does_not_import_user_orm():
    tree = ast.parse(AUTH_API.read_text())

    forbidden_modules = {
        "app.models.models",
        "sqlalchemy",
    }

    violations = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            ast.ImportFrom,
        ):
            module = node.module or ""

            if module in forbidden_modules:
                violations.append(module)

    assert not violations
