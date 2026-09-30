from __future__ import annotations

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

from app.domains.customer_service.services.ai_context_policy import (
    CustomerServiceAIContextPolicy,
)
from app.domains.customer_service.repositories.conversation_intelligence import (
    ConversationInsightRepository,
)
from app.domains.customer_service.services.structured_intelligence import (
    ConversationClassifier,
    OpenAIStructuredConversationClassifier,
    calibrated_confidence,
)


_log = logging.getLogger(__name__)


class ConversationIntelligenceService:
    def __init__(
        self,
        db: AsyncSession,
        policy: CustomerServiceAIContextPolicy | None = None,
        classifier: ConversationClassifier | None = None,
    ):
        self.db = db
        self.repo = ConversationInsightRepository(db)
        self.policy = policy or CustomerServiceAIContextPolicy.from_env()
        self.classifier = classifier
        if (
            classifier is None
            and settings.CS_INTELLIGENCE_MODEL_ENABLED
            and settings.OPENAI_API_KEY
        ):
            self.classifier = OpenAIStructuredConversationClassifier()

    async def analyze(self, user_id, conversation_id, force_refresh: bool = False):
        conversation = await self.repo.get_conversation_with_messages(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if conversation is None:
            return None

        all_messages = sorted(
            conversation.messages,
            key=lambda message: message.created_at,
        )

        latest_message_at = all_messages[-1].created_at if all_messages else None

        messages = all_messages[-self.policy.intelligence_scan_message_limit :]
        total_message_count = await self.repo.get_conversation_message_count(
            user_id=user_id,
            conversation_id=conversation_id,
        )
        if total_message_count is None:
            total_message_count = len(all_messages)

        if not force_refresh:
            existing = await self.repo.get_latest(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            if existing is not None and (
                latest_message_at is None or existing.created_at >= latest_message_at
            ):
                return existing

        full_text = self.policy.trim_text(
            "\\n".join(message.body for message in messages)
        )
        lowered_full = full_text.lower()

        customer_messages = [
            m
            for m in messages
            if getattr(m.sender_type, "value", str(m.sender_type)).lower() == "customer"
        ]

        latest_customer_text = (
            customer_messages[-1].body if customer_messages else full_text
        )

        lowered_latest = latest_customer_text.lower()

        intent = self._detect_intent(lowered_latest)
        sentiment = self._detect_sentiment(lowered_latest)
        urgency = self._detect_urgency(lowered_latest)
        language = self._detect_language(latest_customer_text)
        confidence = self._confidence(
            intent=intent, sentiment=sentiment, urgency=urgency
        )
        root_cause = self._detect_root_cause(lowered_full)
        entities = self._extract_entities(lowered_full)
        risks = self._detect_risks(lowered_full, sentiment, urgency)
        source = "rule"
        model_version = None
        fallback_reason = None

        if self.classifier is not None and latest_customer_text.strip():
            try:
                classification = await self.classifier.classify(
                    self.policy.trim_text(latest_customer_text)
                )
                intent = classification.intent
                sentiment = classification.sentiment
                urgency = classification.urgency
                language = classification.language.lower()
                confidence = calibrated_confidence(classification)
                root_cause = classification.root_cause or root_cause
                entities["order_refs"] = list(
                    dict.fromkeys(
                        [*classification.order_refs, *entities.get("order_refs", [])]
                    )
                )
                entities["classification_reason"] = classification.reason
                risks["model_risk"] = classification.risk
                source = "structured_model"
                model_version = self.classifier.model_version
            except Exception as exc:
                fallback_reason = type(exc).__name__
                source = "rule_fallback"
                _log.warning(
                    "customer_service_intelligence_model_fallback",
                    extra={"failure_type": fallback_reason},
                )

        return await self.repo.upsert(
            user_id=user_id,
            conversation_id=conversation_id,
            sentiment=sentiment,
            intent=intent,
            urgency=urgency,
            summary=self._summarize(messages, total_message_count=total_message_count),
            root_cause=root_cause,
            entities=entities,
            risks=risks,
            opportunities=self._detect_opportunities(lowered_full),
            confidence=confidence,
            source=source,
            language=language,
            model_version=model_version,
            fallback_reason=fallback_reason,
        )

    async def list_for_conversation(self, user_id, conversation_id):
        return await self.repo.list_for_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

    def _detect_intent(self, text: str) -> str:

        if any(
            word in text
            for word in [
                "refund",
                "money back",
                "chargeback",
                "بازپرداخت",
                "پس گرفتن پول",
                "reembolso",
                "remboursement",
                "استرجاع",
            ]
        ):
            return "refund_request"

        if any(
            word in text
            for word in [
                "cancel",
                "cancellation",
                "cancel order",
                "لغو سفارش",
                "cancelar pedido",
                "annuler la commande",
                "إلغاء الطلب",
            ]
        ):
            return "cancellation_request"

        if any(
            word in text
            for word in [
                "damaged",
                "broken",
                "defective",
                "arrived damaged",
                "آسیب دیده",
                "خراب رسیده",
                "dañado",
                "endommagé",
                "تالف",
            ]
        ):
            return "damaged_item"

        if any(
            word in text
            for word in [
                "tracking",
                "track my order",
                "tracking number",
                "where is order",
                "where's my order",
                "where is my order",
                "سفارشم کجاست",
                "پیگیری سفارش",
                "dónde está mi pedido",
                "où est ma commande",
                "أين طلبي",
            ]
        ):
            return "tracking_request"

        if any(
            word in text
            for word in [
                "late",
                "delay",
                "not arrived",
                "shipping delay",
                "تاخیر در ارسال",
                "دیر رسیده",
                "retraso",
                "retard de livraison",
                "تأخر الشحن",
            ]
        ):
            return "shipping_delay"

        if any(
            word in text
            for word in [
                "return",
                "exchange",
                "مرجوع",
                "تعویض",
                "devolución",
                "échange",
                "إرجاع",
            ]
        ):
            return "return_exchange"

        if any(
            word in text
            for word in [
                "billing",
                "charged twice",
                "payment issue",
                "invoice",
            ]
        ):
            return "billing_issue"

        return "general_support"

    def _detect_language(self, text: str) -> str:
        if re.search(r"[\u0600-\u06ff]", text):
            # Persian-specific letters distinguish fa from generic Arabic.
            return "fa" if re.search(r"[پچژگکی]", text) else "ar"
        lowered = text.lower()
        if any(token in lowered for token in ["pedido", "reembolso", "gracias"]):
            return "es"
        if any(token in lowered for token in ["commande", "remboursement", "merci"]):
            return "fr"
        if re.search(r"[a-z]", lowered):
            return "en"
        return "und"

    def _detect_sentiment(self, text: str) -> str:
        negative_words = [
            "angry",
            "bad",
            "terrible",
            "worst",
            "upset",
            "frustrated",
            "damaged",
            "broken",
            "late",
            "عصبانی",
            "افتضاح",
            "خراب",
            "دیر",
            "غاضب",
            "enojado",
            "malo",
        ]
        positive_words = [
            "thanks",
            "great",
            "perfect",
            "happy",
            "love",
            "ممنون",
            "عالی",
            "gracias",
            "merci",
            "شكرا",
        ]

        if any(word in text for word in negative_words):
            return "negative"

        if any(word in text for word in positive_words):
            return "positive"

        return "neutral"

    def _detect_urgency(self, text: str) -> str:
        if any(
            word in text
            for word in [
                "urgent",
                "asap",
                "immediately",
                "now",
                "chargeback",
                "فوری",
                "همین الان",
                "urgente",
                "عاجل",
            ]
        ):
            return "high"

        if any(word in text for word in ["soon", "today", "quickly"]):
            return "medium"

        return "normal"

    def _detect_root_cause(self, text: str) -> str | None:
        if "damaged" in text or "broken" in text:
            return "Product arrived damaged or defective."

        if "late" in text or "not arrived" in text or "delay" in text:
            return "Delivery or shipping delay."

        if "refund" in text:
            return "Customer is requesting money back."

        return None

    def _extract_entities(self, text: str) -> dict:
        entities = {
            "products": [],
            "order_refs": [],
            "keywords": [],
        }

        for keyword in [
            "refund",
            "damaged",
            "broken",
            "late",
            "return",
            "exchange",
            "cancel",
            "address",
            "shipping",
            "tracking",
        ]:
            if keyword in text:
                entities["keywords"].append(keyword)

        order_patterns = [
            r"#\d{3,}",
            r"\border\s*#?\s*(\d{3,})\b",
            r"\bord[-_ ]?(\d{3,})\b",
        ]

        refs = []
        for pattern in order_patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = match.group(0)
                if match.groups():
                    value = match.group(1)
                value = str(value).strip()
                if value and not value.startswith("#") and value.isdigit():
                    value = f"#{value}"
                refs.append(value)

        entities["order_refs"] = list(dict.fromkeys(refs))

        return entities

    def _detect_risks(self, text: str, sentiment: str, urgency: str) -> dict:
        risks = {
            "churn_risk": "low",
            "reputation_risk": "low",
            "revenue_risk": "low",
        }

        if sentiment == "negative":
            risks["churn_risk"] = "medium"

        if urgency == "high":
            risks["revenue_risk"] = "medium"

        if "chargeback" in text or "bad review" in text:
            risks["reputation_risk"] = "high"
            risks["revenue_risk"] = "high"

        return risks

    def _detect_opportunities(self, text: str) -> dict:
        opportunities = {
            "save_customer": False,
            "offer_discount": False,
            "request_review": False,
        }

        if any(word in text for word in ["damaged", "late", "refund", "angry"]):
            opportunities["save_customer"] = True

        if "thanks" in text or "happy" in text:
            opportunities["request_review"] = True

        return opportunities

    def _summarize(self, messages, *, total_message_count: int | None = None) -> str:
        if not messages:
            return "No conversation messages available."

        latest = messages[-1].body.strip()

        if len(latest) > 240:
            latest = latest[:237] + "..."

        count = (
            total_message_count if total_message_count is not None else len(messages)
        )
        return f"Conversation contains {count} message(s). Latest message: {latest}"

    def _confidence(self, intent: str, sentiment: str, urgency: str) -> float:
        score = 0.55

        if intent != "general_support":
            score += 0.2

        if sentiment != "neutral":
            score += 0.1

        if urgency != "normal":
            score += 0.1

        return min(score, 0.95)
