from app.runtime.capabilities.execution.verification.contracts import (
    TaskVerificationContext,
    TaskVerificationEvidence,
    TaskVerificationExecution,
    TaskVerificationMethod,
    TaskVerificationOutcome,
    TaskVerificationRequest,
    TaskVerificationResult,
    TaskVerifier,
)
from app.runtime.capabilities.execution.verification.defaults import (
    build_default_task_verifier_registry,
)
from app.runtime.capabilities.execution.verification.providers import (
    ShopifyCancelOutcomeVerifier,
    ShopifyRefundPreparationVerifier,
    register_shopify_task_verifiers,
)
from app.runtime.capabilities.execution.verification.registry import (
    TaskVerifierRegistry,
)

from app.runtime.capabilities.execution.verification.events import (
    TASK_OUTCOME_INCONCLUSIVE_EVENT,
    TASK_OUTCOME_NOT_ACHIEVED_EVENT,
    TASK_OUTCOME_NOT_VERIFIABLE_EVENT,
    TASK_OUTCOME_PARTIALLY_VERIFIED_EVENT,
    TASK_OUTCOME_VERIFIED_EVENT,
    TASK_VERIFICATION_COMPLETED_EVENT,
    TASK_VERIFICATION_EVENT_SOURCE,
    TASK_VERIFICATION_FAILED_EVENT,
    TaskVerificationLifecycleEvents,
)
from app.runtime.capabilities.execution.verification.service import (
    TaskVerificationService,
)

from app.runtime.capabilities.execution.verification.repository import (
    TaskVerificationRepository,
    normalize_verification_id,
    normalize_verification_idempotency_key,
    normalize_verification_user_id,
)


__all__ = [
    "ShopifyCancelOutcomeVerifier",
    "ShopifyRefundPreparationVerifier",
    "TASK_OUTCOME_INCONCLUSIVE_EVENT",
    "TASK_OUTCOME_NOT_ACHIEVED_EVENT",
    "TASK_OUTCOME_NOT_VERIFIABLE_EVENT",
    "TASK_OUTCOME_PARTIALLY_VERIFIED_EVENT",
    "TASK_OUTCOME_VERIFIED_EVENT",
    "TASK_VERIFICATION_COMPLETED_EVENT",
    "TASK_VERIFICATION_EVENT_SOURCE",
    "TASK_VERIFICATION_FAILED_EVENT",
    "TaskVerificationContext",
    "TaskVerificationEvidence",
    "TaskVerificationMethod",
    "TaskVerificationOutcome",
    "TaskVerificationRequest",
    "TaskVerificationExecution",
    "TaskVerificationLifecycleEvents",
    "TaskVerificationService",
    "TaskVerificationRepository",
    "normalize_verification_id",
    "normalize_verification_idempotency_key",
    "normalize_verification_user_id",
    "TaskVerificationResult",
    "TaskVerifier",
    "TaskVerifierRegistry",
    "build_default_task_verifier_registry",
    "register_shopify_task_verifiers",
]
