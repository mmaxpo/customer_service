import ast
from pathlib import Path


KNOWLEDGE_API = Path("app/api/knowledge.py")


def test_knowledge_http_has_no_direct_sql_or_transaction_implementation():
    text = KNOWLEDGE_API.read_text()

    forbidden = (
        "db.execute(",
        "db.commit(",
        "db.flush(",
        "db.add(",
        "text(",
        "DELETE FROM kb_chunks",
        "SELECT doc_id",
    )

    violations = [marker for marker in forbidden if marker in text]

    assert not violations, (
        f"knowledge HTTP adapter owns persistence implementation: {violations}"
    )


def test_knowledge_http_does_not_import_sql_expression_primitives():
    tree = ast.parse(KNOWLEDGE_API.read_text())

    violations = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "sqlalchemy":
            violations.extend(alias.name for alias in node.names)

    assert not violations


def test_knowledge_http_delegates_document_operations():
    text = KNOWLEDGE_API.read_text()

    assert "delete_knowledge_document(" in text

    assert "list_knowledge_documents(" in text
