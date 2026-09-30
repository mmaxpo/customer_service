from app.domains.customer_service.workflows.message_classifier import (
    CustomerServiceMessageClassifier,
)
from app.domains.customer_service.workflows.schemas import SupportIntent


def test_missing_arrival_is_shipping():
    classifier = CustomerServiceMessageClassifier()

    examples = (
        "My order hasn't arrived.",
        "My order has not arrived.",
        "My package didn't arrive.",
        "My package did not arrive.",
        "My order never arrived.",
    )

    for message in examples:
        result = classifier.classify(message)

        assert result.intent == SupportIntent.SHIPPING, message


def test_arrived_damaged_remains_damaged_product():
    classifier = CustomerServiceMessageClassifier()

    examples = (
        "My product arrived damaged.",
        "My item arrived damaged and broken.",
        "My order arrived broken.",
    )

    for message in examples:
        result = classifier.classify(message)

        assert result.intent == SupportIntent.DAMAGED_PRODUCT, message
