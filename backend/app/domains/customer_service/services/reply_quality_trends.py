from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domains.customer_service.repositories.reply_quality import (
    ReplyQualityRepository,
)


class ReplyQualityTrendsService:
    def __init__(self, db):
        self.db = db

    async def get_trends(self, *, user_id):
        reviews = await ReplyQualityRepository(self.db).list_for_user(
            user_id=user_id,
            limit=5000,
        )

        now = datetime.now(timezone.utc)

        return {
            "last_7_days": self._window(reviews, now=now, days=7),
            "last_30_days": self._window(reviews, now=now, days=30),
        }

    def _window(self, reviews, *, now, days: int):
        cutoff = now - timedelta(days=days)

        rows = [
            review
            for review in reviews
            if review.created_at and review.created_at >= cutoff
        ]

        total = len(rows)
        accepted = len(
            [
                review
                for review in rows
                if review.outcome in {"accepted_without_edit", "accepted_with_edit"}
            ]
        )
        edited = len(
            [review for review in rows if review.outcome == "accepted_with_edit"]
        )
        rejected = len([review for review in rows if review.outcome == "rejected"])

        return {
            "total_reviews": total,
            "acceptance_rate": round(accepted / total, 4) if total else 0.0,
            "edit_rate": round(edited / total, 4) if total else 0.0,
            "rejection_rate": round(rejected / total, 4) if total else 0.0,
        }
