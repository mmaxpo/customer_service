from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeRecord,
)


class CustomerSupportOutcomeConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class CustomerSupportOutcomeWriteResult:
    record: CustomerSupportOutcomeRecord
    created: bool


class CustomerSupportOutcomeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_user(
        self, *, user_id: UUID, outcome_id: UUID
    ) -> CustomerSupportOutcomeRecord | None:
        result = await self.db.execute(
            select(CustomerSupportOutcomeRecord).where(
                CustomerSupportOutcomeRecord.id == outcome_id,
                CustomerSupportOutcomeRecord.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_review_plan_for_user(
        self, *, user_id: UUID, review_plan_id: str
    ) -> CustomerSupportOutcomeRecord | None:
        result = await self.db.execute(
            select(CustomerSupportOutcomeRecord).where(
                CustomerSupportOutcomeRecord.user_id == user_id,
                CustomerSupportOutcomeRecord.review_plan_id == review_plan_id,
            )
        )
        return result.scalar_one_or_none()

    async def record_once(
        self, *, values: dict
    ) -> CustomerSupportOutcomeWriteResult:
        user_id = values["user_id"]
        review_plan_id = values["review_plan_id"]
        incoming_json = values["outcome_json"]

        existing = await self.get_by_review_plan_for_user(
            user_id=user_id,
            review_plan_id=review_plan_id,
        )
        if existing is not None:
            self._require_equivalent(existing, incoming_json)
            return CustomerSupportOutcomeWriteResult(existing, False)

        record = CustomerSupportOutcomeRecord(**values)
        try:
            async with self.db.begin_nested():
                self.db.add(record)
                await self.db.flush()
        except IntegrityError:
            existing = await self.get_by_review_plan_for_user(
                user_id=user_id,
                review_plan_id=review_plan_id,
            )
            if existing is None:
                raise
            self._require_equivalent(existing, incoming_json)
            return CustomerSupportOutcomeWriteResult(existing, False)

        await self.db.refresh(record)
        return CustomerSupportOutcomeWriteResult(record, True)

    @staticmethod
    def _require_equivalent(
        existing: CustomerSupportOutcomeRecord,
        incoming_json: dict,
    ) -> None:
        if existing.outcome_json != incoming_json:
            raise CustomerSupportOutcomeConflictError(
                "Support outcome identity already exists with different facts: "
                f"user_id={existing.user_id} review_plan_id={existing.review_plan_id}"
            )
