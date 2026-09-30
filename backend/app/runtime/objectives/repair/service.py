from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveRepairExecutionRecord,
)
from app.platform.events.publisher import (
    PlatformEventPublisher,
)
from app.runtime.objectives.repair.contracts import (
    ObjectiveRepairPlan,
    ObjectiveRepairRequest,
)
from app.runtime.objectives.repair.repository import (
    ObjectiveRepairExecutionRepository,
)


OBJECTIVE_REPAIR_PLANNED_EVENT = (
    "runtime.objective.repair.planned"
)

OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED = (
    "planned"
)
OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED = (
    "queued"
)
OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING = (
    "running"
)
OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED = (
    "paused"
)
OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED = (
    "completed"
)
OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED = (
    "rejected"
)
OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED = (
    "failed"
)

OBJECTIVE_REPAIR_EXECUTION_TERMINAL_STATUSES = frozenset(
    {
        OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED,
        OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED,
        OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED,
    }
)


class ObjectiveRepairExecutionConflictError(
    RuntimeError
):
    pass


class ObjectiveRepairExecutionNotFoundError(
    LookupError
):
    pass


class ObjectiveRepairExecutionTransitionError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class ObjectiveRepairExecutionWrite:
    record: ObjectiveRepairExecutionRecord
    created: bool
    event_id: UUID | None


class ObjectiveRepairExecutionService:
    """
    Persist immutable repair requests and plans.

    This service owns generic repair-planning truth only. It
    does not build or launch product workflows.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: (
            ObjectiveRepairExecutionRepository | None
        ) = None,
    ) -> None:
        self.db = db
        self.repository = (
            repository
            or ObjectiveRepairExecutionRepository(db)
        )

    async def record_plan(
        self,
        *,
        source_event_id: UUID,
        user_id: UUID,
        tenant_id: str | None,
        resolution_record_id: UUID,
        request: ObjectiveRepairRequest,
        plan: ObjectiveRepairPlan,
        planner_ref: str,
        planner_policy_version: int,
        attempt_number: int = 1,
        commit: bool = True,
    ) -> ObjectiveRepairExecutionWrite:
        normalized_planner_ref = str(
            planner_ref or ""
        ).strip()

        if not normalized_planner_ref:
            raise ValueError(
                "objective repair planner_ref is required"
            )

        if planner_policy_version < 1:
            raise ValueError(
                "planner_policy_version must be >= 1"
            )

        if attempt_number < 1:
            raise ValueError(
                "attempt_number must be >= 1"
            )

        self._validate_request_plan(
            request=request,
            plan=plan,
        )

        request_json = request.model_dump(
            mode="json"
        )
        plan_json = plan.model_dump(
            mode="json"
        )

        request_version = self._schema_version_number(
            request.schema_version,
            expected_prefix=(
                "objective_repair_request.v"
            ),
        )
        plan_version = self._schema_version_number(
            plan.schema_version,
            expected_prefix=(
                "objective_repair_plan.v"
            ),
        )

        values = {
            "source_event_id": source_event_id,
            "user_id": user_id,
            "tenant_id": (
                str(tenant_id).strip()
                if tenant_id is not None
                and str(tenant_id).strip()
                else None
            ),
            "resolution_record_id": (
                resolution_record_id
            ),
            "objective_namespace": (
                request.source.objective.namespace
            ),
            "objective_type": (
                request.source.objective
                .objective_type
            ),
            "objective_ref": (
                request.source.objective
                .objective_ref
            ),
            "objective_version": (
                request.source.objective
                .objective_version
            ),
            "repair_request_ref": (
                request.repair_request_ref
            ),
            "repair_request_version": (
                request_version
            ),
            "repair_plan_version": plan_version,
            "planner_ref": normalized_planner_ref,
            "planner_policy_version": (
                planner_policy_version
            ),
            "controlling_disposition": (
                plan.disposition.value
            ),
            "status": (
                OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED
            ),
            "target_count": len(request.targets),
            "planned_target_count": len(
                plan.planned_target_refs
            ),
            "deferred_target_count": len(
                plan.deferred_target_refs
            ),
            "unhandled_target_count": len(
                plan.unhandled_target_refs
            ),
            "requires_human_approval": (
                plan.human_approval_required
            ),
            "automatic_execution_allowed": (
                plan.automatic_execution_allowed
            ),
            "request_json": request_json,
            "plan_json": plan_json,
            "workflow_json": None,
            "workflow_job_id": None,
            "workflow_run_id": None,
            "attempt_number": attempt_number,
        }

        record, created = await self.repository.record(
            values=values,
        )

        if not created:
            self._assert_equivalent(
                existing=record,
                expected=values,
            )

        event_id = None

        if created:
            publish_result = await (
                PlatformEventPublisher(self.db).publish(
                    event_type=(
                        OBJECTIVE_REPAIR_PLANNED_EVENT
                    ),
                    source=(
                        "runtime.objective_repair"
                    ),
                    user_id=user_id,
                    payload={
                        "repair_execution_id": str(
                            record.id
                        ),
                        "resolution_record_id": str(
                            resolution_record_id
                        ),
                        "repair_request_ref": (
                            request.repair_request_ref
                        ),
                        "objective_namespace": (
                            record.objective_namespace
                        ),
                        "objective_type": (
                            record.objective_type
                        ),
                        "objective_ref": (
                            record.objective_ref
                        ),
                        "objective_version": (
                            record.objective_version
                        ),
                        "controlling_disposition": (
                            record
                            .controlling_disposition
                        ),
                        "attempt_number": (
                            record.attempt_number
                        ),
                        "target_count": (
                            record.target_count
                        ),
                        "requires_human_approval": (
                            record
                            .requires_human_approval
                        ),
                        "automatic_execution_allowed": (
                            record
                            .automatic_execution_allowed
                        ),
                    },
                    meta={
                        "source_event_id": str(
                            source_event_id
                        ),
                        "planner_ref": (
                            normalized_planner_ref
                        ),
                        "planner_policy_version": (
                            planner_policy_version
                        ),
                    },
                    dispatch=True,
                    commit=False,
                )
            )

            event_id = publish_result["event"].id

        if commit:
            await self.db.commit()
            await self.db.refresh(record)
        else:
            await self.db.flush()

        return ObjectiveRepairExecutionWrite(
            record=record,
            created=created,
            event_id=event_id,
        )

    async def queue_workflow(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
        workflow_json: dict,
        workflow_job_id: UUID,
        commit: bool = True,
    ) -> ObjectiveRepairExecutionRecord:
        if not isinstance(workflow_json, dict):
            raise ValueError(
                "objective repair workflow_json must be "
                "an object"
            )

        if not workflow_json:
            raise ValueError(
                "objective repair workflow_json is required"
            )

        record = await self._locked_record(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        if (
            record.status
            == OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED
        ):
            if (
                record.workflow_job_id == workflow_job_id
                and self._canonical(
                    record.workflow_json
                )
                == self._canonical(workflow_json)
            ):
                return await self._finish_write(
                    record=record,
                    commit=commit,
                )

            raise ObjectiveRepairExecutionConflictError(
                "objective repair execution is already "
                "queued with different workflow facts"
            )

        self._require_status(
            record=record,
            allowed={
                OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED,
            },
            target=(
                OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED
            ),
        )

        record.workflow_json = deepcopy(workflow_json)
        record.workflow_job_id = workflow_job_id
        record.status = (
            OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED
        )
        record.result_json = None
        record.failure_code = None
        record.failure_message = None

        return await self._finish_write(
            record=record,
            commit=commit,
        )

    async def mark_running(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
        workflow_run_id: str,
        started_at: datetime | None = None,
        commit: bool = True,
    ) -> ObjectiveRepairExecutionRecord:
        normalized_run_id = self._required_text(
            workflow_run_id,
            "workflow_run_id",
        )
        timestamp = self._timestamp(
            started_at
        )

        record = await self._locked_record(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        if (
            record.status
            == OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING
        ):
            if record.workflow_run_id == normalized_run_id:
                return await self._finish_write(
                    record=record,
                    commit=commit,
                )

            raise ObjectiveRepairExecutionConflictError(
                "objective repair execution is running "
                "under a different workflow run"
            )

        self._require_status(
            record=record,
            allowed={
                OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED,
                OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED,
            },
            target=(
                OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING
            ),
        )

        if (
            record.workflow_run_id is not None
            and record.workflow_run_id
            != normalized_run_id
        ):
            raise ObjectiveRepairExecutionConflictError(
                "objective repair workflow_run_id cannot "
                "change after attachment"
            )

        record.workflow_run_id = normalized_run_id
        record.status = (
            OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING
        )

        if record.launched_at is None:
            record.launched_at = timestamp

        return await self._finish_write(
            record=record,
            commit=commit,
        )

    async def mark_paused(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
        workflow_run_id: str,
        result_json: dict | None = None,
        commit: bool = True,
    ) -> ObjectiveRepairExecutionRecord:
        normalized_run_id = self._required_text(
            workflow_run_id,
            "workflow_run_id",
        )

        record = await self._locked_record(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        if (
            record.workflow_run_id is not None
            and record.workflow_run_id
            != normalized_run_id
        ):
            raise ObjectiveRepairExecutionConflictError(
                "objective repair pause belongs to a "
                "different workflow run"
            )

        if (
            record.status
            == OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED
        ):
            if self._canonical(
                record.result_json
            ) == self._canonical(result_json):
                return await self._finish_write(
                    record=record,
                    commit=commit,
                )

            raise ObjectiveRepairExecutionConflictError(
                "objective repair pause was already "
                "recorded with different result facts"
            )

        self._require_status(
            record=record,
            allowed={
                OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING,
            },
            target=(
                OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED
            ),
        )

        record.workflow_run_id = normalized_run_id
        record.status = (
            OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED
        )
        record.result_json = self._optional_json(
            result_json
        )

        return await self._finish_write(
            record=record,
            commit=commit,
        )

    async def mark_completed(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
        workflow_run_id: str,
        result_json: dict,
        completed_at: datetime | None = None,
        commit: bool = True,
    ) -> ObjectiveRepairExecutionRecord:
        return await self._mark_terminal(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
            workflow_run_id=workflow_run_id,
            target_status=(
                OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED
            ),
            result_json=result_json,
            failure_code=None,
            failure_message=None,
            completed_at=completed_at,
            commit=commit,
        )

    async def mark_rejected(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
        workflow_run_id: str,
        result_json: dict,
        completed_at: datetime | None = None,
        commit: bool = True,
    ) -> ObjectiveRepairExecutionRecord:
        return await self._mark_terminal(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
            workflow_run_id=workflow_run_id,
            target_status=(
                OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED
            ),
            result_json=result_json,
            failure_code=None,
            failure_message=None,
            completed_at=completed_at,
            commit=commit,
        )

    async def mark_failed(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
        failure_code: str,
        failure_message: str,
        workflow_run_id: str | None = None,
        result_json: dict | None = None,
        completed_at: datetime | None = None,
        commit: bool = True,
    ) -> ObjectiveRepairExecutionRecord:
        normalized_code = self._required_text(
            failure_code,
            "failure_code",
        ).lower()
        normalized_message = self._required_text(
            failure_message,
            "failure_message",
        )

        return await self._mark_terminal(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
            workflow_run_id=workflow_run_id,
            target_status=(
                OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED
            ),
            result_json=result_json,
            failure_code=normalized_code,
            failure_message=normalized_message,
            completed_at=completed_at,
            commit=commit,
        )

    async def _mark_terminal(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
        workflow_run_id: str | None,
        target_status: str,
        result_json: dict | None,
        failure_code: str | None,
        failure_message: str | None,
        completed_at: datetime | None,
        commit: bool,
    ) -> ObjectiveRepairExecutionRecord:
        normalized_run_id = (
            self._required_text(
                workflow_run_id,
                "workflow_run_id",
            )
            if workflow_run_id is not None
            else None
        )

        record = await self._locked_record(
            user_id=user_id,
            repair_execution_id=repair_execution_id,
        )

        if record.status == target_status:
            if (
                (
                    normalized_run_id is None
                    or record.workflow_run_id
                    == normalized_run_id
                )
                and self._canonical(
                    record.result_json
                )
                == self._canonical(result_json)
                and record.failure_code
                == failure_code
                and record.failure_message
                == failure_message
            ):
                return await self._finish_write(
                    record=record,
                    commit=commit,
                )

            raise ObjectiveRepairExecutionConflictError(
                "objective repair terminal state was "
                "already recorded with different facts"
            )

        self._require_status(
            record=record,
            allowed={
                OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED,
                OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING,
                OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED,
            },
            target=target_status,
        )

        if (
            normalized_run_id is not None
            and record.workflow_run_id is not None
            and record.workflow_run_id
            != normalized_run_id
        ):
            raise ObjectiveRepairExecutionConflictError(
                "objective repair terminal result belongs "
                "to a different workflow run"
            )

        if normalized_run_id is not None:
            record.workflow_run_id = normalized_run_id

        record.status = target_status
        record.result_json = self._optional_json(
            result_json
        )
        record.failure_code = failure_code
        record.failure_message = failure_message
        record.completed_at = self._timestamp(
            completed_at
        )

        return await self._finish_write(
            record=record,
            commit=commit,
        )

    async def _locked_record(
        self,
        *,
        user_id: UUID,
        repair_execution_id: UUID,
    ) -> ObjectiveRepairExecutionRecord:
        record = await (
            self.repository
            .get_by_id_for_user_for_update(
                user_id=user_id,
                repair_execution_id=repair_execution_id,
            )
        )

        if record is None:
            raise ObjectiveRepairExecutionNotFoundError(
                "objective repair execution was not found"
            )

        return record

    @staticmethod
    def _require_status(
        *,
        record: ObjectiveRepairExecutionRecord,
        allowed: set[str],
        target: str,
    ) -> None:
        if record.status in allowed:
            return

        raise ObjectiveRepairExecutionTransitionError(
            "invalid objective repair execution "
            f"transition: {record.status} -> {target}"
        )

    async def _finish_write(
        self,
        *,
        record: ObjectiveRepairExecutionRecord,
        commit: bool,
    ) -> ObjectiveRepairExecutionRecord:
        if commit:
            await self.db.commit()
            await self.db.refresh(record)
        else:
            await self.db.flush()

        return record

    @staticmethod
    def _timestamp(
        value: datetime | None,
    ) -> datetime:
        timestamp = value or datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            raise ValueError(
                "objective repair lifecycle timestamp "
                "must be timezone-aware"
            )

        return timestamp

    @staticmethod
    def _required_text(
        value: str,
        field_name: str,
    ) -> str:
        normalized = str(value or "").strip()

        if not normalized:
            raise ValueError(
                f"{field_name} is required"
            )

        return normalized

    @staticmethod
    def _optional_json(
        value: dict | None,
    ) -> dict | None:
        if value is None:
            return None

        if not isinstance(value, dict):
            raise ValueError(
                "objective repair result_json must be "
                "an object"
            )

        return deepcopy(value)

    @staticmethod
    def _validate_request_plan(
        *,
        request: ObjectiveRepairRequest,
        plan: ObjectiveRepairPlan,
    ) -> None:
        if (
            plan.repair_request_ref
            != request.repair_request_ref
        ):
            raise ValueError(
                "objective repair plan request ref does "
                "not match request"
            )

        if (
            plan.objective
            != request.source.objective
        ):
            raise ValueError(
                "objective repair plan objective does "
                "not match request"
            )

        request_target_refs = {
            target.operation_ref
            for target in request.targets
        }

        covered_target_refs = (
            set(plan.planned_target_refs)
            | set(plan.deferred_target_refs)
            | set(plan.unhandled_target_refs)
        )

        if covered_target_refs != request_target_refs:
            raise ValueError(
                "objective repair plan target coverage "
                "does not match request"
            )

    @staticmethod
    def _schema_version_number(
        value: str,
        *,
        expected_prefix: str,
    ) -> int:
        normalized = str(value or "").strip()

        if not normalized.startswith(
            expected_prefix
        ):
            raise ValueError(
                "unsupported objective repair schema "
                f"version: {normalized or '<blank>'}"
            )

        raw_version = normalized[
            len(expected_prefix):
        ]

        try:
            version = int(raw_version)
        except ValueError as exc:
            raise ValueError(
                "objective repair schema version must "
                "end with an integer"
            ) from exc

        if version < 1:
            raise ValueError(
                "objective repair schema version must "
                "be >= 1"
            )

        return version

    @classmethod
    def _assert_equivalent(
        cls,
        *,
        existing: ObjectiveRepairExecutionRecord,
        expected: dict[str, Any],
    ) -> None:
        comparable_fields = (
            "user_id",
            "tenant_id",
            "resolution_record_id",
            "objective_namespace",
            "objective_type",
            "objective_ref",
            "objective_version",
            "repair_request_ref",
            "repair_request_version",
            "repair_plan_version",
            "planner_ref",
            "planner_policy_version",
            "controlling_disposition",
            "status",
            "target_count",
            "planned_target_count",
            "deferred_target_count",
            "unhandled_target_count",
            "requires_human_approval",
            "automatic_execution_allowed",
            "request_json",
            "plan_json",
            "attempt_number",
        )

        differences = [
            field_name
            for field_name in comparable_fields
            if cls._canonical(
                getattr(existing, field_name)
            )
            != cls._canonical(
                expected[field_name]
            )
        ]

        if differences:
            raise ObjectiveRepairExecutionConflictError(
                "objective repair execution identity "
                "already exists with different facts: "
                + ", ".join(differences)
            )

    @staticmethod
    def _canonical(value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, dict):
            return {
                key: (
                    ObjectiveRepairExecutionService
                    ._canonical(item)
                )
                for key, item in sorted(
                    value.items()
                )
            }

        if isinstance(value, (list, tuple)):
            return [
                ObjectiveRepairExecutionService
                ._canonical(item)
                for item in value
            ]

        return value


__all__ = [
    "OBJECTIVE_REPAIR_EXECUTION_STATUS_COMPLETED",
    "OBJECTIVE_REPAIR_EXECUTION_STATUS_FAILED",
    "OBJECTIVE_REPAIR_EXECUTION_STATUS_PAUSED",
    "OBJECTIVE_REPAIR_EXECUTION_STATUS_PLANNED",
    "OBJECTIVE_REPAIR_EXECUTION_STATUS_QUEUED",
    "OBJECTIVE_REPAIR_EXECUTION_STATUS_REJECTED",
    "OBJECTIVE_REPAIR_EXECUTION_STATUS_RUNNING",
    "OBJECTIVE_REPAIR_EXECUTION_TERMINAL_STATUSES",
    "OBJECTIVE_REPAIR_PLANNED_EVENT",
    "ObjectiveRepairExecutionConflictError",
    "ObjectiveRepairExecutionNotFoundError",
    "ObjectiveRepairExecutionService",
    "ObjectiveRepairExecutionTransitionError",
    "ObjectiveRepairExecutionWrite",
]
