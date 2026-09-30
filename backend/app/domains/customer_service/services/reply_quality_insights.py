from __future__ import annotations

from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.repositories.reply_quality import (
    ReplyQualityRepository,
)


class ReplyQualityInsightsService:
    def __init__(self, db: AsyncSession):
        self.repo = ReplyQualityRepository(db)

    async def get_insights(self, *, user_id) -> dict:
        reviews = await self.repo.list_for_user(user_id=user_id)

        return {
            "total_reviews": len(reviews),
            "accepted_without_edit": self._count(reviews, "accepted_without_edit"),
            "accepted_with_edit": self._count(reviews, "accepted_with_edit"),
            "rejected": self._count(reviews, "rejected"),
            "acceptance_rate": self._rate(
                self._count(reviews, "accepted_without_edit")
                + self._count(reviews, "accepted_with_edit"),
                len(reviews),
            ),
            "edit_rate": self._rate(
                self._count(reviews, "accepted_with_edit"),
                len(reviews),
            ),
            "rejection_rate": self._rate(
                self._count(reviews, "rejected"),
                len(reviews),
            ),
            "average_score": self._average(
                [review.overall_score for review in reviews]
            ),
            "average_edit_distance": self._average(
                [
                    review.edit_distance
                    for review in reviews
                    if review.edit_distance is not None
                ]
            ),
            "by_reply_type": self._bucket(
                reviews,
                key_getter=lambda review: self._source_value(
                    review,
                    "reply_type",
                    default="unknown",
                ),
            ),
            "by_intent": self._bucket(
                reviews,
                key_getter=lambda review: self._source_value(
                    review,
                    "intent",
                    default="unknown",
                ),
            ),
        }

    def _count(self, reviews, outcome: str) -> int:
        return sum(1 for review in reviews if review.outcome == outcome)

    def _rate(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _average(self, values) -> float | None:
        clean = [value for value in values if value is not None]
        if not clean:
            return None
        return round(sum(clean) / len(clean), 4)

    def _bucket(self, reviews, *, key_getter):
        grouped = defaultdict(list)

        for review in reviews:
            grouped[str(key_getter(review) or "unknown")].append(review)

        return [
            {
                "key": key,
                "total": len(items),
                "accepted_without_edit": self._count(
                    items,
                    "accepted_without_edit",
                ),
                "accepted_with_edit": self._count(
                    items,
                    "accepted_with_edit",
                ),
                "rejected": self._count(items, "rejected"),
                "acceptance_rate": self._rate(
                    self._count(items, "accepted_without_edit")
                    + self._count(items, "accepted_with_edit"),
                    len(items),
                ),
                "edit_rate": self._rate(
                    self._count(items, "accepted_with_edit"),
                    len(items),
                ),
                "rejection_rate": self._rate(
                    self._count(items, "rejected"),
                    len(items),
                ),
                "average_score": self._average([item.overall_score for item in items]),
            }
            for key, items in sorted(grouped.items())
        ]

    def _source_value(self, review, key: str, *, default: str):
        scores = review.scores or {}
        metadata = scores.get("metadata") or {}

        if key in metadata:
            return metadata[key]

        sources = metadata.get("sources") or {}
        if key in sources:
            return sources[key]

        return default
