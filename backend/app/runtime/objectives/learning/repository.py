from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ObjectiveLearningExperienceRecord,
)


class ObjectiveLearningExperienceConflictError(RuntimeError):
    """
    Raised when one semantic extraction identity is reused
    with different immutable experience facts.
    """


def normalize_objective_learning_user_id(
    value: UUID | str,
) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        raise ValueError("user_id must be a valid UUID") from exc


def normalize_objective_learning_record_id(
    value: UUID | str,
    *,
    field_name: str = "resolution_record_id",
) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        raise ValueError(f"{field_name} must be a valid UUID") from exc


def normalize_objective_learning_version(
    value: int,
    *,
    field_name: str,
) -> int:
    try:
        normalized = int(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc

    if normalized < 1:
        raise ValueError(f"{field_name} must be >= 1")

    return normalized


def normalize_required_objective_learning_ref(
    value: Any,
    *,
    field_name: str,
    lowercase: bool = False,
) -> str:
    normalized = str(value).strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty")

    if lowercase:
        normalized = normalized.lower()

    return normalized


def normalize_optional_objective_learning_ref(
    value: Any | None,
) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()

    return normalized or None


class ObjectiveLearningExperienceRepository:
    """
    Append-only persistence for extracted objective-learning
    experiences.

    One semantic extraction identity converges onto one immutable
    row. Identical retries return the existing row. Reusing that
    identity with different facts raises a conflict.

    Writes flush but do not commit unless explicitly requested.
    The repository does not extract experience, publish events,
    enqueue jobs, activate planner guidance, rank candidates, or
    authorize execution.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    async def record(
        self,
        *,
        user_id: UUID | str,
        tenant_id: str | None,
        resolution_record_id: UUID | str,
        objective_namespace: str,
        objective_type: str,
        objective_ref: str,
        objective_version: int,
        schema_ref: str,
        profile_ref: str,
        profile_version: int,
        extractor_ref: str,
        extractor_version: int,
        outcome_ref: str,
        evaluation_ref: str,
        workflow_run_id: str | None,
        dimension_keys: list[str] | tuple[str, ...],
        evidence_refs: list[str] | tuple[str, ...],
        validity_scope: dict[str, Any],
        experience: dict[str, Any],
        informational_only: bool,
        authorizes_execution: bool,
        commit: bool = False,
    ) -> tuple[
        ObjectiveLearningExperienceRecord,
        bool,
    ]:
        values = self._normalize_values(
            user_id=user_id,
            tenant_id=tenant_id,
            resolution_record_id=(resolution_record_id),
            objective_namespace=(objective_namespace),
            objective_type=objective_type,
            objective_ref=objective_ref,
            objective_version=objective_version,
            schema_ref=schema_ref,
            profile_ref=profile_ref,
            profile_version=profile_version,
            extractor_ref=extractor_ref,
            extractor_version=extractor_version,
            outcome_ref=outcome_ref,
            evaluation_ref=evaluation_ref,
            workflow_run_id=workflow_run_id,
            dimension_keys=dimension_keys,
            evidence_refs=evidence_refs,
            validity_scope=validity_scope,
            experience=experience,
            informational_only=(informational_only),
            authorizes_execution=(authorizes_execution),
        )

        statement = (
            insert(ObjectiveLearningExperienceRecord)
            .values(
                id=uuid4(),
                **values,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ObjectiveLearningExperienceRecord.user_id,
                    ObjectiveLearningExperienceRecord.resolution_record_id,
                    ObjectiveLearningExperienceRecord.schema_ref,
                    ObjectiveLearningExperienceRecord.profile_ref,
                    ObjectiveLearningExperienceRecord.profile_version,
                    ObjectiveLearningExperienceRecord.extractor_ref,
                    ObjectiveLearningExperienceRecord.extractor_version,
                ]
            )
            .returning(ObjectiveLearningExperienceRecord.id)
        )

        inserted_id = (await self.db.execute(statement)).scalar_one_or_none()

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

        if inserted_id is not None:
            created = await self.get(record_id=inserted_id)

            if created is None:
                raise RuntimeError(
                    "Inserted objective learning experience could not be read"
                )

            return created, True

        existing = await self.get_by_semantic_identity(
            user_id=values["user_id"],
            resolution_record_id=(values["resolution_record_id"]),
            schema_ref=values["schema_ref"],
            profile_ref=values["profile_ref"],
            profile_version=(values["profile_version"]),
            extractor_ref=(values["extractor_ref"]),
            extractor_version=(values["extractor_version"]),
        )

        if existing is None:
            raise RuntimeError(
                "Objective learning experience "
                "insert conflicted but no existing "
                "row could be resolved"
            )

        self._assert_same_experience(
            existing=existing,
            expected=values,
        )

        return existing, False

    async def get(
        self,
        *,
        record_id: UUID,
    ) -> ObjectiveLearningExperienceRecord | None:
        result = await self.db.execute(
            select(ObjectiveLearningExperienceRecord).where(
                ObjectiveLearningExperienceRecord.id == record_id
            )
        )

        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        *,
        user_id: UUID | str,
        record_id: UUID,
    ) -> ObjectiveLearningExperienceRecord | None:
        normalized_user_id = normalize_objective_learning_user_id(user_id)

        result = await self.db.execute(
            select(ObjectiveLearningExperienceRecord).where(
                ObjectiveLearningExperienceRecord.id == record_id,
                ObjectiveLearningExperienceRecord.user_id == normalized_user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_semantic_identity(
        self,
        *,
        user_id: UUID | str,
        resolution_record_id: UUID | str,
        schema_ref: str,
        profile_ref: str,
        profile_version: int,
        extractor_ref: str,
        extractor_version: int,
    ) -> ObjectiveLearningExperienceRecord | None:
        normalized_user_id = normalize_objective_learning_user_id(user_id)
        normalized_resolution_id = normalize_objective_learning_record_id(
            resolution_record_id
        )

        result = await self.db.execute(
            select(ObjectiveLearningExperienceRecord).where(
                ObjectiveLearningExperienceRecord.user_id == normalized_user_id,
                ObjectiveLearningExperienceRecord.resolution_record_id
                == normalized_resolution_id,
                ObjectiveLearningExperienceRecord.schema_ref
                == (
                    normalize_required_objective_learning_ref(
                        schema_ref,
                        field_name="schema_ref",
                    )
                ),
                ObjectiveLearningExperienceRecord.profile_ref
                == (
                    normalize_required_objective_learning_ref(
                        profile_ref,
                        field_name="profile_ref",
                    )
                ),
                ObjectiveLearningExperienceRecord.profile_version
                == (
                    normalize_objective_learning_version(
                        profile_version,
                        field_name=("profile_version"),
                    )
                ),
                ObjectiveLearningExperienceRecord.extractor_ref
                == (
                    normalize_required_objective_learning_ref(
                        extractor_ref,
                        field_name="extractor_ref",
                    )
                ),
                ObjectiveLearningExperienceRecord.extractor_version
                == (
                    normalize_objective_learning_version(
                        extractor_version,
                        field_name=("extractor_version"),
                    )
                ),
            )
        )

        return result.scalar_one_or_none()

    async def list_for_aggregation(
        self,
        *,
        user_id: UUID | str,
        window_hours: int = 720,
        tenant_id: str | None = None,
        objective_namespace: str | None = None,
        objective_type: str | None = None,
        objective_version: int | None = None,
        schema_ref: str | None = None,
        profile_ref: str | None = None,
        profile_version: int | None = None,
        extractor_ref: str | None = None,
        extractor_version: int | None = None,
        now: datetime | None = None,
    ) -> tuple[
        datetime,
        datetime,
        list[ObjectiveLearningExperienceRecord],
    ]:
        """
        Return immutable experiences from one bounded user scope.

        This method performs retrieval only. It does not aggregate,
        persist summaries, publish events, enqueue jobs, or authorize
        planning or execution behavior.
        """

        normalized_user_id = normalize_objective_learning_user_id(user_id)

        if window_hours < 1 or window_hours > 8760:
            raise ValueError("window_hours must be between 1 and 8760")

        window_end = now or datetime.now(timezone.utc)

        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=timezone.utc)

        window_start = window_end - timedelta(hours=window_hours)

        normalized_tenant_id = (
            normalize_optional_objective_learning_ref(tenant_id)
            if tenant_id is not None
            else None
        )

        normalized_objective_namespace = (
            normalize_required_objective_learning_ref(
                objective_namespace,
                field_name="objective namespace",
            )
            if objective_namespace is not None
            else None
        )

        normalized_objective_type = (
            normalize_required_objective_learning_ref(
                objective_type,
                field_name="objective type",
            )
            if objective_type is not None
            else None
        )

        normalized_schema_ref = (
            normalize_required_objective_learning_ref(
                schema_ref,
                field_name="schema ref",
            )
            if schema_ref is not None
            else None
        )

        normalized_profile_ref = (
            normalize_required_objective_learning_ref(
                profile_ref,
                field_name="profile ref",
            )
            if profile_ref is not None
            else None
        )

        normalized_extractor_ref = (
            normalize_required_objective_learning_ref(
                extractor_ref,
                field_name="extractor ref",
            )
            if extractor_ref is not None
            else None
        )

        normalized_objective_version = (
            normalize_objective_learning_version(
                objective_version,
                field_name="objective version",
            )
            if objective_version is not None
            else None
        )

        normalized_profile_version = (
            normalize_objective_learning_version(
                profile_version,
                field_name="profile version",
            )
            if profile_version is not None
            else None
        )

        normalized_extractor_version = (
            normalize_objective_learning_version(
                extractor_version,
                field_name="extractor version",
            )
            if extractor_version is not None
            else None
        )

        stmt = (
            select(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == normalized_user_id,
                ObjectiveLearningExperienceRecord.created_at >= window_start,
                ObjectiveLearningExperienceRecord.created_at < window_end,
            )
            .order_by(
                ObjectiveLearningExperienceRecord.created_at.asc(),
                ObjectiveLearningExperienceRecord.id.asc(),
            )
        )

        filters = (
            (
                ObjectiveLearningExperienceRecord.tenant_id,
                normalized_tenant_id,
            ),
            (
                ObjectiveLearningExperienceRecord.objective_namespace,
                normalized_objective_namespace,
            ),
            (
                ObjectiveLearningExperienceRecord.objective_type,
                normalized_objective_type,
            ),
            (
                ObjectiveLearningExperienceRecord.objective_version,
                normalized_objective_version,
            ),
            (
                ObjectiveLearningExperienceRecord.schema_ref,
                normalized_schema_ref,
            ),
            (
                ObjectiveLearningExperienceRecord.profile_ref,
                normalized_profile_ref,
            ),
            (
                ObjectiveLearningExperienceRecord.profile_version,
                normalized_profile_version,
            ),
            (
                ObjectiveLearningExperienceRecord.extractor_ref,
                normalized_extractor_ref,
            ),
            (
                ObjectiveLearningExperienceRecord.extractor_version,
                normalized_extractor_version,
            ),
        )

        for column, value in filters:
            if value is not None:
                stmt = stmt.where(column == value)

        result = await self.db.execute(stmt)

        return (
            window_start,
            window_end,
            list(result.scalars().all()),
        )

    async def list_for_resolution(
        self,
        *,
        user_id: UUID | str,
        resolution_record_id: UUID | str,
        limit: int = 100,
    ) -> list[ObjectiveLearningExperienceRecord]:
        """
        Return immutable extraction history for one authenticated
        user's exact objective resolution.

        Results are ordered by profile and extractor versions,
        followed by durable creation time and record identity.
        This method is read-only and performs no mutation, locking,
        extraction, publication, or commit.
        """

        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")

        normalized_user_id = normalize_objective_learning_user_id(user_id)
        normalized_resolution_id = normalize_objective_learning_record_id(
            resolution_record_id
        )

        result = await self.db.execute(
            select(ObjectiveLearningExperienceRecord)
            .where(
                ObjectiveLearningExperienceRecord.user_id == normalized_user_id,
                ObjectiveLearningExperienceRecord.resolution_record_id
                == normalized_resolution_id,
            )
            .order_by(
                ObjectiveLearningExperienceRecord.profile_version.asc(),
                ObjectiveLearningExperienceRecord.extractor_version.asc(),
                ObjectiveLearningExperienceRecord.created_at.asc(),
                ObjectiveLearningExperienceRecord.id.asc(),
            )
            .limit(limit)
        )

        return list(result.scalars().all())

    @staticmethod
    def experience_from_record(
        record: ObjectiveLearningExperienceRecord,
    ) -> dict[str, Any]:
        return deepcopy(dict(record.experience_json or {}))

    @staticmethod
    def _normalize_values(
        *,
        user_id: UUID | str,
        tenant_id: str | None,
        resolution_record_id: UUID | str,
        objective_namespace: str,
        objective_type: str,
        objective_ref: str,
        objective_version: int,
        schema_ref: str,
        profile_ref: str,
        profile_version: int,
        extractor_ref: str,
        extractor_version: int,
        outcome_ref: str,
        evaluation_ref: str,
        workflow_run_id: str | None,
        dimension_keys: list[str] | tuple[str, ...],
        evidence_refs: list[str] | tuple[str, ...],
        validity_scope: dict[str, Any],
        experience: dict[str, Any],
        informational_only: bool,
        authorizes_execution: bool,
    ) -> dict[str, Any]:
        if not informational_only:
            raise ValueError(
                "objective learning experience must remain informational only"
            )

        if authorizes_execution:
            raise ValueError("objective learning experience cannot authorize execution")

        normalized_dimension_keys = [
            normalize_required_objective_learning_ref(
                value,
                field_name="dimension key",
            )
            for value in dimension_keys
        ]

        if len(normalized_dimension_keys) != len(set(normalized_dimension_keys)):
            raise ValueError("dimension keys must be unique")

        if not normalized_dimension_keys:
            raise ValueError("dimension keys must not be empty")

        normalized_evidence_refs = [
            normalize_required_objective_learning_ref(
                value,
                field_name="evidence ref",
            )
            for value in evidence_refs
        ]

        if not normalized_evidence_refs:
            raise ValueError("evidence refs must not be empty")

        normalized_experience = deepcopy(dict(experience))
        normalized_validity_scope = deepcopy(dict(validity_scope))

        if not normalized_experience:
            raise ValueError("experience must not be empty")

        if not normalized_validity_scope:
            raise ValueError("validity_scope must not be empty")

        return {
            "user_id": (normalize_objective_learning_user_id(user_id)),
            "tenant_id": (normalize_optional_objective_learning_ref(tenant_id)),
            "resolution_record_id": (
                normalize_objective_learning_record_id(resolution_record_id)
            ),
            "objective_namespace": (
                normalize_required_objective_learning_ref(
                    objective_namespace,
                    field_name=("objective_namespace"),
                    lowercase=True,
                )
            ),
            "objective_type": (
                normalize_required_objective_learning_ref(
                    objective_type,
                    field_name="objective_type",
                    lowercase=True,
                )
            ),
            "objective_ref": (
                normalize_required_objective_learning_ref(
                    objective_ref,
                    field_name="objective_ref",
                )
            ),
            "objective_version": (
                normalize_objective_learning_version(
                    objective_version,
                    field_name="objective_version",
                )
            ),
            "schema_ref": (
                normalize_required_objective_learning_ref(
                    schema_ref,
                    field_name="schema_ref",
                )
            ),
            "profile_ref": (
                normalize_required_objective_learning_ref(
                    profile_ref,
                    field_name="profile_ref",
                )
            ),
            "profile_version": (
                normalize_objective_learning_version(
                    profile_version,
                    field_name="profile_version",
                )
            ),
            "extractor_ref": (
                normalize_required_objective_learning_ref(
                    extractor_ref,
                    field_name="extractor_ref",
                )
            ),
            "extractor_version": (
                normalize_objective_learning_version(
                    extractor_version,
                    field_name="extractor_version",
                )
            ),
            "outcome_ref": (
                normalize_required_objective_learning_ref(
                    outcome_ref,
                    field_name="outcome_ref",
                )
            ),
            "evaluation_ref": (
                normalize_required_objective_learning_ref(
                    evaluation_ref,
                    field_name="evaluation_ref",
                )
            ),
            "workflow_run_id": (
                normalize_optional_objective_learning_ref(workflow_run_id)
            ),
            "dimension_keys_json": (normalized_dimension_keys),
            "evidence_refs_json": (normalized_evidence_refs),
            "validity_scope_json": (normalized_validity_scope),
            "experience_json": (normalized_experience),
            "informational_only": True,
            "authorizes_execution": False,
        }

    @staticmethod
    def _assert_same_experience(
        *,
        existing: ObjectiveLearningExperienceRecord,
        expected: dict[str, Any],
    ) -> None:
        scalar_fields = (
            "user_id",
            "tenant_id",
            "resolution_record_id",
            "objective_namespace",
            "objective_type",
            "objective_ref",
            "objective_version",
            "schema_ref",
            "profile_ref",
            "profile_version",
            "extractor_ref",
            "extractor_version",
            "outcome_ref",
            "evaluation_ref",
            "workflow_run_id",
            "informational_only",
            "authorizes_execution",
        )

        for field_name in scalar_fields:
            if getattr(existing, field_name) != expected[field_name]:
                raise (
                    ObjectiveLearningExperienceConflictError(
                        "Objective learning semantic "
                        "identity already exists with "
                        "different experience facts"
                    )
                )

        json_fields = (
            "dimension_keys_json",
            "evidence_refs_json",
            "validity_scope_json",
            "experience_json",
        )

        for field_name in json_fields:
            if getattr(existing, field_name) != expected[field_name]:
                raise (
                    ObjectiveLearningExperienceConflictError(
                        "Objective learning semantic "
                        "identity already exists with "
                        "different experience facts"
                    )
                )


__all__ = [
    "ObjectiveLearningExperienceConflictError",
    "ObjectiveLearningExperienceRepository",
    "normalize_objective_learning_record_id",
    "normalize_objective_learning_user_id",
    "normalize_objective_learning_version",
]
