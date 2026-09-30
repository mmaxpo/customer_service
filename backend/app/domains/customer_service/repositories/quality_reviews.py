from sqlalchemy import select

from app.domains.customer_service.models import CustomerServiceQualityReview


class QualityReviewRepository:
    def __init__(self, db):

        self.db = db

    async def create(self, **kwargs):

        obj = CustomerServiceQualityReview(**kwargs)

        self.db.add(obj)

        await self.db.commit()

        await self.db.refresh(obj)

        return obj

    async def list(self, user_id, conversation_id):

        result = await self.db.execute(
            select(CustomerServiceQualityReview).where(
                CustomerServiceQualityReview.user_id == user_id,
                CustomerServiceQualityReview.conversation_id == conversation_id,
            )
        )

        return result.scalars().all()
