from app.domains.customer_service.workflows.schemas import (
    MessageClassification,
    SupportIntent,
)


class CustomerServiceMessageClassifier:
    def classify(self, text: str) -> MessageClassification:
        value = text.lower()

        if "refund" in value or "money back" in value:
            return MessageClassification(
                intent=SupportIntent.REFUND,
                confidence=0.9,
                reason="Message mentions refund request.",
            )

        if (
            "where is" in value
            or "shipping" in value
            or "package" in value
            or "delivery" in value
            or "order status" in value
            or "status of order" in value
            or ("order" in value and "status" in value)
            or "track order" in value
            or "track my order" in value
            or "tracking" in value
            or "shipped" in value
            or "check order" in value
            or "hasn't arrived" in value
            or "has not arrived" in value
            or "didn't arrive" in value
            or "did not arrive" in value
            or "never arrived" in value
        ):
            return MessageClassification(
                intent=SupportIntent.SHIPPING,
                confidence=0.85,
                reason="Message is about shipping or delivery.",
            )

        if "cancel" in value or "subscription" in value:
            return MessageClassification(
                intent=SupportIntent.CANCELLATION,
                confidence=0.85,
                reason="Message asks for cancellation.",
            )

        if "damaged" in value or "broken" in value or "wrong item" in value:
            return MessageClassification(
                intent=SupportIntent.DAMAGED_PRODUCT,
                confidence=0.9,
                reason="Message reports damaged or wrong product.",
            )

        return MessageClassification(
            intent=SupportIntent.GENERAL,
            confidence=0.5,
            reason="No specific support intent matched.",
        )
