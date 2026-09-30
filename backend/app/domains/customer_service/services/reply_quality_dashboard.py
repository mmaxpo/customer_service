from __future__ import annotations

from app.domains.customer_service.services.reply_quality_insights import (
    ReplyQualityInsightsService,
)


class ReplyQualityDashboardService:
    def __init__(self, db):
        self.db = db

    async def dashboard(self, *, user_id):
        insights = await ReplyQualityInsightsService(self.db).get_insights(
            user_id=user_id
        )

        reply_types = insights["by_reply_type"]
        intents = insights["by_intent"]

        return {
            "best_reply_types": sorted(
                reply_types,
                key=lambda x: (
                    x["acceptance_rate"],
                    x["average_score"] or 0,
                ),
                reverse=True,
            )[:5],
            "worst_reply_types": sorted(
                reply_types,
                key=lambda x: (
                    x["acceptance_rate"],
                    x["average_score"] or 0,
                ),
            )[:5],
            "best_intents": sorted(
                intents,
                key=lambda x: (
                    x["acceptance_rate"],
                    x["average_score"] or 0,
                ),
                reverse=True,
            )[:5],
            "worst_intents": sorted(
                intents,
                key=lambda x: (
                    x["acceptance_rate"],
                    x["average_score"] or 0,
                ),
            )[:5],
            "high_edit_reply_types": sorted(
                reply_types,
                key=lambda x: x["edit_rate"],
                reverse=True,
            )[:5],
            "high_rejection_intents": sorted(
                intents,
                key=lambda x: x["rejection_rate"],
                reverse=True,
            )[:5],
        }
