from app.domains.customer_service.services.automation_activity import (
    CustomerServiceAutomationActivityService,
)
from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)
from app.domains.customer_service.services.structured_intelligence import (
    StructuredConversationClassification,
    calibrated_confidence,
)


def test_deterministic_fallback_understands_persian_customer_intents():
    service = ConversationIntelligenceService.__new__(ConversationIntelligenceService)

    assert service._detect_language("سفارشم کجاست؟") == "fa"
    assert service._detect_intent("سفارشم کجاست؟") == "tracking_request"
    assert service._detect_intent("می خواهم بازپرداخت بگیرم") == "refund_request"


def test_structured_confidence_is_conservatively_calibrated():
    classification = StructuredConversationClassification(
        intent="general_support",
        sentiment="neutral",
        urgency="normal",
        language="und",
        confidence=0.97,
        reason="No supported intent was clear.",
        risk="low",
    )

    assert calibrated_confidence(classification) == 0.6


def test_activity_projection_redacts_provider_secrets_and_categorizes_evidence():
    service = CustomerServiceAutomationActivityService.__new__(
        CustomerServiceAutomationActivityService
    )

    assert service._category("shopify provider capability completed") == "provider_call"
    assert service._category("objective repair planned") == "repair"
    assert service._category("human approval waiting") == "approval"
    assert service._sanitize({"access_token": "secret", "order_id": "123"}) == {
        "access_token": "[redacted]",
        "order_id": "123",
    }

