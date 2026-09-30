from app.domains.customer_service.services.conversation_intelligence import (
    ConversationIntelligenceService,
)

from app.domains.customer_service.repositories.quality_reviews import (
    QualityReviewRepository,
)


class QualityReviewService:
    def __init__(self, db):

        self.db = db

        self.repo = QualityReviewRepository(db)

    async def review(self, user_id, conversation_id):

        intelligence = await ConversationIntelligenceService(self.db).analyze(
            user_id=user_id, conversation_id=conversation_id
        )

        scores = {}

        issues = []

        recommendations = []

        scores["tone"] = 70
        scores["professionalism"] = 80
        scores["resolution_quality"] = 75
        scores["empathy"] = 70

        if intelligence.sentiment == "negative":
            scores["empathy"] = 50

            issues.append("Customer sentiment negative")

            recommendations.append("Acknowledge frustration")

        if intelligence.urgency == "high":
            recommendations.append("Escalate faster")

        overall = sum(scores.values()) / len(scores)

        return await self.repo.create(
            user_id=user_id,
            conversation_id=conversation_id,
            overall_score=overall,
            scores=scores,
            issues=issues,
            recommendations=recommendations,
            reviewer_type="rule",
        )

    async def list(self, user_id, conversation_id):
        return await self.repo.list(user_id=user_id, conversation_id=conversation_id)
