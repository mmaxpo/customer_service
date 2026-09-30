from pathlib import Path


def test_no_conversation_ticket_lazy_access():
    root = Path("app/domains/customer_service")

    offenders = []

    for path in root.rglob("*.py"):
        text = path.read_text()

        if "conversation.ticket" in text:
            offenders.append(str(path))

    assert offenders == []
