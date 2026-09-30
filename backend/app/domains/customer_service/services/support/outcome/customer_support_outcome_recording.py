from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.models.outcomes import (
    CustomerSupportOutcomeRecord,
)
from app.domains.customer_service.repositories.chat_repository import ChatRepository
from app.domains.customer_service.repositories.customer_support_outcomes import (
    CustomerSupportOutcomeRepository,
)
from app.domains.customer_service.services.support.outcome.customer_support_outcome import (
    CustomerSupportOutcome,
    SupportOutcomeStatus,
)
from app.platform.events.publisher import PlatformEventPublisher


SUPPORT_OUTCOME_RECORDED_EVENT = "customer_service.support.outcome.recorded"


@dataclass(frozen=True)
class CustomerSupportOutcomeRecordingResult:
    record: CustomerSupportOutcomeRecord
    created: bool
    event_id: UUID | None


class CustomerSupportOutcomeRecordingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = CustomerSupportOutcomeRepository(db)
        self.chat_repository = ChatRepository(db)

    async def record(
        self,
        *,
        user_id: UUID,
        workflow_run_id: UUID,
        chat_session_id: UUID,
        outcome: CustomerSupportOutcome,
        source_objective_version: int,
        recording_idempotency_key: str | None = None,
    ) -> CustomerSupportOutcomeRecordingResult:
        session = await self.chat_repository.get_session(chat_session_id)
        if session is None or session.user_id != user_id:
            raise ValueError("Support outcome chat session ownership mismatch")

        link = await self.chat_repository.get_inbox_link_for_session(
            session_id=chat_session_id
        )
        if link is None or link.user_id != user_id:
            raise ValueError("Support outcome inbox bridge is required")

        outcome_json = outcome.model_dump(mode="json")
        objective_type = self._objective_type(outcome)
        status = self._aggregate_status(outcome)

        write = await self.repository.record_once(
            values={
                "user_id": user_id,
                "review_plan_id": outcome.review_plan_id,
                "workflow_run_id": workflow_run_id,
                "chat_session_id": chat_session_id,
                "conversation_id": link.conversation_id,
                "objective_namespace": "customer_service.support",
                "objective_ref": outcome.review_plan_id,
                "source_objective_version": source_objective_version,
                "outcome_version": outcome.version,
                "objective_type": objective_type,
                "order_ref": outcome.order_ref,
                "decision": outcome.decision,
                "status": status,
                "operation_count": len(outcome.operations),
                "customer_message": outcome.customer_message,
                "operations_json": [
                    item.model_dump(mode="json") for item in outcome.operations
                ],
                "outcome_json": outcome_json,
                "recording_idempotency_key": recording_idempotency_key,
            }
        )

        event_id = None
        if write.created:
            publish_result = await PlatformEventPublisher(self.db).publish(
                event_type=SUPPORT_OUTCOME_RECORDED_EVENT,
                source="customer_service.support_outcome",
                user_id=user_id,
                payload={
                    "outcome_id": str(write.record.id),
                    "review_plan_id": outcome.review_plan_id,
                    "conversation_id": str(link.conversation_id),
                    "chat_session_id": str(chat_session_id),
                    "objective_type": objective_type,
                    "decision": outcome.decision,
                    "status": status,
                    "operation_count": len(outcome.operations),
                },
                meta={
                    "workflow_run_id": str(workflow_run_id),
                    "recording_idempotency_key": recording_idempotency_key,
                },
                dispatch=True,
                commit=False,
            )
            event_id = publish_result["event"].id

        await self.db.commit()
        await self.db.refresh(write.record)
        return CustomerSupportOutcomeRecordingResult(
            record=write.record,
            created=write.created,
            event_id=event_id,
        )

    @staticmethod
    def _objective_type(outcome: CustomerSupportOutcome) -> str:
        types = [item.operation_type.value for item in outcome.operations]
        if not types:
            return "unknown"
        if len(types) == 1:
            return types[0]
        return "multi_operation"

    @staticmethod
    def _aggregate_status(outcome: CustomerSupportOutcome) -> str:
        if outcome.decision == "rejected":
            return SupportOutcomeStatus.REJECTED.value
        statuses = [item.status for item in outcome.operations]
        if any(item == SupportOutcomeStatus.FAILED for item in statuses):
            return SupportOutcomeStatus.FAILED.value
        if statuses and all(item == SupportOutcomeStatus.COMPLETED for item in statuses):
            return SupportOutcomeStatus.COMPLETED.value
        if any(item == SupportOutcomeStatus.SUBMITTED for item in statuses):
            return SupportOutcomeStatus.SUBMITTED.value
        if any(item == SupportOutcomeStatus.PREPARED for item in statuses):
            return SupportOutcomeStatus.PREPARED.value
        return SupportOutcomeStatus.UNKNOWN.value
