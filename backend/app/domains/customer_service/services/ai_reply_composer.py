from __future__ import annotations


class CustomerServiceAIReplyComposer:
    def _compose_shopify_order_reply(
        self,
        *,
        customer_message: str,
        shopify_context: dict,
        intelligence,
    ) -> dict | None:
        order_name = shopify_context.get("order_name") or shopify_context.get(
            "order_id"
        )
        financial_status = shopify_context.get("financial_status")
        fulfillment_status = shopify_context.get("fulfillment_status")
        total_price = shopify_context.get("total_price")
        currency = shopify_context.get("currency")
        tracking = shopify_context.get("tracking") or {}

        is_paid = bool(shopify_context.get("is_paid"))
        is_fulfilled = bool(shopify_context.get("is_fulfilled"))
        tracking_number = tracking.get("tracking_number")
        tracking_url = tracking.get("tracking_url")
        carrier = tracking.get("carrier")

        text = customer_message.lower()
        is_tracking_request = any(
            phrase in text
            for phrase in [
                "tracking",
                "where is my order",
                "where is order",
                "check tracking",
                "paid but",
                "shipment",
                "shipping",
            ]
        )

        if not order_name or not is_tracking_request:
            return None

        lines = [
            "Hi, thanks for reaching out.",
            "",
            f"I checked {order_name} for you.",
        ]

        if is_paid:
            lines.append("The order is paid successfully.")
        elif financial_status:
            lines.append(f"The payment status is currently {financial_status}.")

        if tracking_number:
            tracking_line = f"Tracking is available: {tracking_number}"
            if carrier:
                tracking_line += f" with {carrier}"
            tracking_line += "."
            lines.append(tracking_line)

            if tracking_url:
                lines.append(f"You can track it here: {tracking_url}")
        elif not is_fulfilled:
            lines.append(
                "It has not been fulfilled yet, so Shopify does not have tracking information for it yet."
            )
            lines.append(
                "I will keep this open for review so the fulfillment team can confirm when tracking will be available."
            )
        else:
            lines.append(
                "The order appears fulfilled, but I do not see tracking information attached yet."
            )
            lines.append(
                "I will check this with the fulfillment team and follow up with the tracking details."
            )

        if total_price and currency:
            lines.append("")
            lines.append(f"Order total: {total_price} {currency}.")

        return {
            "body": "\n".join(lines),
            "confidence": 0.9,
            "reply_type": "shopify_order_tracking",
            "requires_review": True,
            "source_summary": {
                "has_knowledge": False,
                "knowledge_hit_count": 0,
                "has_shopify_context": True,
                "intent": getattr(intelligence, "intent", None),
                "sentiment": getattr(intelligence, "sentiment", None),
                "urgency": getattr(intelligence, "urgency", None),
            },
            "sources": {
                "knowledge_hits": [],
                "shopify_context": shopify_context,
                "intent": getattr(intelligence, "intent", None),
                "sentiment": getattr(intelligence, "sentiment", None),
                "urgency": getattr(intelligence, "urgency", None),
            },
        }

    def compose(
        self,
        *,
        customer_message: str,
        intelligence,
        knowledge_context: dict | None = None,
        shopify_context: dict | None = None,
    ) -> dict:
        if shopify_context:
            shopify_reply = self._compose_shopify_order_reply(
                customer_message=customer_message,
                shopify_context=shopify_context,
                intelligence=intelligence,
            )
            if shopify_reply is not None:
                return shopify_reply

        knowledge_context = knowledge_context or {}
        shopify_context = shopify_context or {}

        intent = getattr(intelligence, "intent", None) or "general_support"
        sentiment = getattr(intelligence, "sentiment", None) or "neutral"
        urgency = getattr(intelligence, "urgency", None) or "normal"

        parts = ["Hi, thanks for reaching out."]

        if shopify_context.get("found"):
            order = shopify_context.get("order") or {}
            payload = order.get("payload") or {}
            order_name = order.get("order_name") or payload.get("name")
            fulfillment = payload.get("fulfillment_status")
            financial = payload.get("financial_status")

            if order_name:
                parts.append(f"I found your order {order_name}.")

            if intent in {"shipping_delay", "shipping_status"}:
                if fulfillment:
                    parts.append(f"The current fulfillment status is {fulfillment}.")
                else:
                    parts.append("I’m checking the latest shipping status for you.")

            if intent == "refund_request":
                if financial:
                    parts.append(f"The order payment status is {financial}.")
                parts.append(
                    "I can help review the refund request and next available options."
                )

        context = (knowledge_context.get("context") or "").strip()
        if context:
            parts.append("Based on our support information, the relevant guidance is:")
            parts.append(context[:900])

        if sentiment == "negative" or urgency == "high":
            parts.append(
                "I understand this is frustrating, and I’ll help get this resolved as quickly as possible."
            )

        parts.append(
            "Could you confirm if there is anything else I should check for this order?"
        )

        body = "\n\n".join(parts)

        confidence = 0.84 if shopify_context.get("found") or context else 0.68

        return {
            "body": body,
            "confidence": confidence,
            "reply_type": self._reply_type(
                intent=intent, shopify_context=shopify_context
            ),
            "requires_review": confidence < 0.9,
            "source_summary": {
                "has_knowledge": bool(context),
                "knowledge_hit_count": len(knowledge_context.get("hits") or []),
                "has_shopify_context": bool(shopify_context.get("found")),
                "intent": intent,
                "sentiment": sentiment,
                "urgency": urgency,
            },
            "sources": {
                "knowledge_hits": knowledge_context.get("hits") or [],
                "shopify_context": shopify_context,
                "intent": intent,
                "sentiment": sentiment,
                "urgency": urgency,
            },
        }

    def _reply_type(self, *, intent: str, shopify_context: dict) -> str:
        if intent in {"shipping_delay", "shipping_status"}:
            return "shipping_status"

        if intent == "refund_request":
            return "refund_review"

        if intent == "cancellation":
            return "cancellation_review"

        if intent == "damaged_item":
            return "damaged_item_review"

        if shopify_context.get("found"):
            return "order_context"

        return "general_support"
