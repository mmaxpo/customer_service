from app.domains.customer_service.services.ai_reply_composer import (
    CustomerServiceAIReplyComposer,
)


class Intelligence:
    intent = "refund_request"
    sentiment = "negative"
    urgency = "high"


def test_ai_reply_composer_returns_metadata():
    result = CustomerServiceAIReplyComposer().compose(
        customer_message="I want a refund",
        intelligence=Intelligence(),
        knowledge_context={
            "context": "Refunds are reviewed within 3 business days.",
            "hits": [{"id": "kb1"}],
        },
        shopify_context={
            "found": True,
            "order": {
                "order_name": "#1001",
                "payload": {
                    "financial_status": "paid",
                },
            },
        },
    )

    assert result["reply_type"] == "refund_review"
    assert result["requires_review"] is True

    summary = result["source_summary"]

    assert summary["has_knowledge"] is True
    assert summary["knowledge_hit_count"] == 1
    assert summary["has_shopify_context"] is True
    assert summary["intent"] == "refund_request"
