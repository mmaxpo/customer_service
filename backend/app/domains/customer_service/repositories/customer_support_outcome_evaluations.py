from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeEvaluationRecord,
)


@dataclass(frozen=True)
class CustomerSupportOutcomeEvaluationWrite:
    record: CustomerSupportOutcomeEvaluationRecord
    created: bool


class CustomerSupportOutcomeEvaluationRepository:
    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def get(
        self,
        *,
        user_id: UUID,
        evaluation_id: UUID,
    ) -> (
        CustomerSupportOutcomeEvaluationRecord
        | None
    ):
        result = await self.db.execute(
            select(
                CustomerSupportOutcomeEvaluationRecord
            ).where(
                CustomerSupportOutcomeEvaluationRecord.id
                == evaluation_id,
                CustomerSupportOutcomeEvaluationRecord
                .user_id
                == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_outcome_version(
        self,
        *,
        user_id: UUID,
        support_outcome_id: UUID,
        evaluation_version: int,
    ) -> (
        CustomerSupportOutcomeEvaluationRecord
        | None
    ):
        result = await self.db.execute(
            select(
                CustomerSupportOutcomeEvaluationRecord
            ).where(
                CustomerSupportOutcomeEvaluationRecord
                .user_id
                == user_id,
                CustomerSupportOutcomeEvaluationRecord
                .support_outcome_id
                == support_outcome_id,
                CustomerSupportOutcomeEvaluationRecord
                .evaluation_version
                == evaluation_version,
            )
        )
        return result.scalar_one_or_none()

    async def record_once(
        self,
        *,
        values: dict,
    ) -> CustomerSupportOutcomeEvaluationWrite:
        existing = await (
            self.get_by_outcome_version(
                user_id=values["user_id"],
                support_outcome_id=(
                    values["support_outcome_id"]
                ),
                evaluation_version=(
                    values["evaluation_version"]
                ),
            )
        )

        if existing is not None:
            return (
                CustomerSupportOutcomeEvaluationWrite(
                    record=existing,
                    created=False,
                )
            )

        record = (
            CustomerSupportOutcomeEvaluationRecord(
                **values
            )
        )

        try:
            async with self.db.begin_nested():
                self.db.add(record)
                await self.db.flush()
        except IntegrityError:
            existing = await (
                self.get_by_outcome_version(
                    user_id=values["user_id"],
                    support_outcome_id=(
                        values[
                            "support_outcome_id"
                        ]
                    ),
                    evaluation_version=(
                        values[
                            "evaluation_version"
                        ]
                    ),
                )
            )

            if existing is None:
                raise

            return (
                CustomerSupportOutcomeEvaluationWrite(
                    record=existing,
                    created=False,
                )
            )

        await self.db.refresh(record)

        return CustomerSupportOutcomeEvaluationWrite(
            record=record,
            created=True,
        )


__all__ = [
    "CustomerSupportOutcomeEvaluationRepository",
    "CustomerSupportOutcomeEvaluationWrite",
]
