from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models import CustomerServiceQualityReview


class ReplyQualityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> CustomerServiceQualityReview:
        review = CustomerServiceQualityReview(**kwargs)
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def list_for_conversation(self, *, user_id, conversation_id):
        result = await self.db.execute(
            select(CustomerServiceQualityReview)
            .where(
                CustomerServiceQualityReview.user_id == user_id,
                CustomerServiceQualityReview.conversation_id == conversation_id,
                CustomerServiceQualityReview.review_type == "ai_reply",
            )
            .order_by(CustomerServiceQualityReview.created_at.desc())
        )
        return list(result.scalars().all())

    async def aggregate_metrics(self, *, user_id):
        result = await self.db.execute(
            select(
                func.count(CustomerServiceQualityReview.id),
                func.sum(
                    func.cast(
                        CustomerServiceQualityReview.outcome == "accepted_without_edit",
                        type_=__import__("sqlalchemy").Integer,
                    )
                ),
                func.sum(
                    func.cast(
                        CustomerServiceQualityReview.outcome == "accepted_with_edit",
                        type_=__import__("sqlalchemy").Integer,
                    )
                ),
                func.sum(
                    func.cast(
                        CustomerServiceQualityReview.outcome == "rejected",
                        type_=__import__("sqlalchemy").Integer,
                    )
                ),
                func.avg(CustomerServiceQualityReview.overall_score),
                func.avg(CustomerServiceQualityReview.accuracy_score),
                func.avg(CustomerServiceQualityReview.relevance_score),
                func.avg(CustomerServiceQualityReview.tone_score),
            ).where(
                CustomerServiceQualityReview.user_id == user_id,
                CustomerServiceQualityReview.review_type == "ai_reply",
            )
        )

        row = result.one()

        return {
            "total_reviews": int(row[0] or 0),
            "accepted_without_edit": int(row[1] or 0),
            "accepted_with_edit": int(row[2] or 0),
            "rejected": int(row[3] or 0),
            "average_score": float(row[4]) if row[4] is not None else None,
            "average_accuracy_score": float(row[5]) if row[5] is not None else None,
            "average_relevance_score": float(row[6]) if row[6] is not None else None,
            "average_tone_score": float(row[7]) if row[7] is not None else None,
        }

    async def list_for_user(
        self,
        user_id,
        limit: int = 1000,
    ):

        result = await self.db.execute(
            select(CustomerServiceQualityReview)
            .where(
                CustomerServiceQualityReview.user_id == user_id,
                CustomerServiceQualityReview.review_type == "ai_reply",
            )
            .order_by(CustomerServiceQualityReview.created_at.desc())
            .limit(limit)
        )

        return result.scalars().all()
