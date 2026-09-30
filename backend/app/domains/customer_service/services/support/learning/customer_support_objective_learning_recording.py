from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.customer_service.services.support.learning.customer_support_objective_learning_source_loader import (
    CustomerSupportObjectiveLearningSourceLoader,
)
from app.domains.customer_service.services.support.learning.objective_learning_extraction import (
    CustomerSupportObjectiveLearningExperience,
    CustomerSupportObjectiveLearningSource,
    extract_customer_support_objective_learning,
)
from app.domains.customer_service.services.support.learning.objective_learning_profiles import (
    build_customer_support_objective_learning_profile,
)
from app.models.models import (
    ObjectiveLearningExperienceRecord,
)
from app.runtime.objectives.learning import (
    ObjectiveLearningExperienceRepository,
    ObjectiveLearningProfile,
)


@dataclass(frozen=True)
class CustomerSupportObjectiveLearningRecordingResult:
    """
    Product-owned result for one canonical learning extraction.

    The result reports durable persistence truth and preserves the
    exact canonical source and extracted experience used to create
    or resolve the immutable generic record.
    """

    record: ObjectiveLearningExperienceRecord
    created: bool
    source: CustomerSupportObjectiveLearningSource
    experience: CustomerSupportObjectiveLearningExperience


class CustomerSupportObjectiveLearningRecordingService:
    """
    Load, extract, and durably record customer-support learning.

    This product service owns canonical source loading and the
    mapping from customer-support extraction contracts into the
    generic objective-learning repository.

    Persistence remains informational only. This service does not
    publish an event, enqueue a job, activate planner guidance,
    alter ranking, authorize execution, or bypass verification.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        source_loader: (CustomerSupportObjectiveLearningSourceLoader | None) = None,
        repository: (ObjectiveLearningExperienceRepository | None) = None,
        profile: ObjectiveLearningProfile | None = None,
    ) -> None:
        self.db = db
        self.source_loader = (
            source_loader or CustomerSupportObjectiveLearningSourceLoader(db)
        )
        self.repository = repository or ObjectiveLearningExperienceRepository(db)
        self.profile = profile or build_customer_support_objective_learning_profile()

    async def record_for_resolution(
        self,
        *,
        user_id: UUID,
        resolution_record_id: UUID,
        tenant_id: str | None = None,
    ) -> CustomerSupportObjectiveLearningRecordingResult:
        """
        Record one canonical extraction for an objective resolution.

        The canonical loader validates owner, tenant, outcome,
        evaluation, review-plan, workflow, and repair lineage before
        extraction. The complete extraction snapshot is then mapped
        into the generic append-only repository.
        """

        try:
            source = await self.source_loader.load_for_resolution(
                user_id=user_id,
                resolution_record_id=(resolution_record_id),
                tenant_id=tenant_id,
            )

            experience = extract_customer_support_objective_learning(
                profile=self.profile,
                source=source,
            )

            payload = experience.model_dump(mode="json")
            validity_scope = payload["validity_scope"]
            scope_metadata = dict(validity_scope.get("metadata") or {})

            record, created = await self.repository.record(
                user_id=payload["user_id"],
                tenant_id=(validity_scope.get("tenant_id")),
                resolution_record_id=(payload["resolution_record_id"]),
                objective_namespace=(validity_scope["objective_namespace"]),
                objective_type=(validity_scope["objective_type"]),
                objective_ref=(payload["objective_ref"]),
                objective_version=(validity_scope["objective_version"]),
                schema_ref=(payload["schema_ref"]),
                profile_ref=(payload["profile_ref"]),
                profile_version=(payload["profile_version"]),
                extractor_ref=(payload["extractor_ref"]),
                extractor_version=(payload["extractor_version"]),
                outcome_ref=(payload["outcome_ref"]),
                evaluation_ref=(payload["evaluation_ref"]),
                workflow_run_id=(scope_metadata.get("workflow_run_id")),
                dimension_keys=[item["key"] for item in payload["dimensions"]],
                evidence_refs=list(payload["evidence_refs"]),
                validity_scope=(validity_scope),
                experience=payload,
                informational_only=(payload["informational_only"]),
                authorizes_execution=(payload["authorizes_execution"]),
                commit=False,
            )

            await self.db.commit()
            await self.db.refresh(record)

            return CustomerSupportObjectiveLearningRecordingResult(
                record=record,
                created=created,
                source=source,
                experience=experience,
            )
        except Exception:
            await self.db.rollback()
            raise


__all__ = [
    "CustomerSupportObjectiveLearningRecordingResult",
    "CustomerSupportObjectiveLearningRecordingService",
]
