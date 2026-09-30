# Feature: AI Quality / Outcomes

## Spec
- **What it should do:** Every meaningful AI interaction produces a structured outcome (successful/failed/escalated/human-corrected/customer-reopened/action-failed/policy-conflict) that can later be evaluated.
- **Layer:** core
- **Likely location (guess — verify, I don't have your repo):** app/tcos outcome recording (request → decision → action → result → outcome pipeline)
- **Key entities:** AI Interaction, Request, Decision, Action, Result, Outcome, Evaluation, Correction, Escalation
- **Core rules to check against:** Outcome must represent actual result, not AI assumption; human corrections distinguishable; customer reopening is an important negative signal; action failure must not equal successful resolution; outcome records traceable to the interaction

## Acceptance criteria (from the v1 spec's "DONE" list)
- Every supported AI interaction has an outcome lifecycle
- Success/failure/escalation distinguishable; human correction and customer reopen recorded
- Action success separate from answer success; basic evaluation exists
- Outcome traceable to conversation/run/action; tests cover outcome transitions

## Production success condition
> Tajeran can tell not merely what its AI did, but whether the customer-service task actually succeeded.

## Audit Result
_Filled in by `/audit-feature ai-quality-outcomes`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**

**Core layer (app/runtime, app/tcos):**
- **CapabilityExecutionOutcome** (`app/runtime/capabilities/execution/outcomes.py`) — outcome for capability invocations with status (SUCCEEDED/FAILED), ok flag, provider_ref, error details, duration, user_id, tenant_id
- **CapabilityOutcomeReporter** (`app/runtime/capabilities/execution/reporting.py`) — protocol for reporting outcomes; implementations include InMemoryCapabilityOutcomeReporter, PlatformCapabilityOutcomeReporter
- **ObjectiveResolutionRecord** (`app/models/models.py`) — immutable durable projection of evaluated objectives with source_outcome_ref, evaluation_ref, assessment_json, workflow_run_id, user_id, tenant_id
- **TaskVerificationOutcome** (`app/runtime/capabilities/execution/verification/contracts.py`) — outcome enum for task verification

**Product layer (customer_service):**
- **CustomerSupportOutcomeRecord** (`app/domains/customer_service/models/outcomes.py`) — canonical immutable outcome for support review with review_plan_id, workflow_run_id, conversation_id, decision, status, operation_count, outcome_json, recording_idempotency_key
- **CustomerSupportOutcomeEvaluationRecord** — evaluation of outcome with result (ACHIEVED/PARTIALLY_ACHIEVED/PROGRESSING/FAILED/INTENTIONALLY_NOT_EXECUTED/INCONCLUSIVE), reason_code, confidence, achieved/failed/pending/unknown/not_executed operation counts, evidence_json
- **CustomerSupportOutcomeRecordingService** (`app/domains/customer_service/services/support/outcome/`) — records outcomes with idempotency; publishes SUPPORT_OUTCOME_RECORDED_EVENT
- **CustomerSupportOutcomeEvaluationService** — evaluates outcomes using CustomerSupportOutcomeEvaluator
- **CustomerSupportOutcomeEvaluator** — deterministic evaluation logic that counts operations and determines result
- **AgentAssistSuggestion** (`app/domains/customer_service/models/quality.py`) — tracks agent suggestions with status (GENERATED, REVIEWED, APPROVED, REJECTED, SENT), reviewed_by, approved_by fields
- Tests exist for outcome recording, evaluation, persistence covering basic transitions

**Is it good enough?**
- **Mostly yes, but with gaps.** Outcome recording and evaluation exist with proper tracking.
  - ✓ Every AI interaction (support review) produces an outcome (CustomerSupportOutcomeRecord)
  - ✓ Success/failure/escalation distinguishable (evaluation_result enum covers these states)
  - ✓ Action success separate from answer success (operation_count vs. decision tracking)
  - ✓ Outcome traceable (workflow_run_id, conversation_id, review_plan_id indexed)
  - ✓ Basic evaluation exists (CustomerSupportOutcomeEvaluator with confidence scoring)
  - ⚠️ **Missing:** No explicit outcome for escalation actions (e.g., when AI declines to act)
  - ⚠️ **Missing:** Human correction tracking (evaluation records don't capture human override)
  - ⚠️ **Missing:** Customer reopening signal (no outcome lifecycle that tracks customer re-engagement)
  - ⚠️ **Weak:** Outcome status field is string, not enum (allows arbitrary values)
  - ⚠️ **Unclear:** How action failures are distinguished from resolution failures (both map to "failed")

**Gaps / risks:**
- **Escalation outcomes unclear:** When AI escalates (e.g., insufficient confidence, missing context), is an outcome recorded? Spec mentions "escalated" as an outcome type. Currently only ACHIEVED/FAILED patterns found.
- **Human correction not recorded:** AgentAssistSuggestion tracks reviewed_by/approved_by for agent suggestions, but no outcome field for "human corrected the AI's action." Evaluation result enum doesn't include "human_corrected" or similar.
- **Customer reopening signal missing:** No outcome lifecycle field or separate record for customer reopening ticket/conversation after AI interaction. This is a critical negative signal per spec but not captured in models.
- **Action failure vs. resolution failure:** Evaluation counts "failed_operation_count" but doesn't distinguish between "operation failed (e.g., refund API error)" and "operation succeeded but customer still unsatisfied." Risk: false positives claiming success.
- **Outcome status field untyped:** CustomerSupportOutcomeRecord.status is String(32), not an enum. Allows "prepared" / "submitted" / "completed" / "failed" but no validation. Risk: typos, inconsistent spellings.
- **Outcome coverage gap:** Only customer_service.support outcomes found. What about agent_assist suggestions that are sent but not reviewed? What about conversations that end without a formal review plan?
- **Policy conflict outcome missing:** Spec mentions "policy-conflict" as outcome type. Not found in CustomerSupportOutcomeEvaluationResult enum.
- **Evaluation coverage incomplete:** Evaluator only examines CustomerSupportOutcomeRecord (support reviews). No evaluation for: escalations, agent suggestions, failed actions outside refund/cancellation context.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **Escalation outcome:** Add outcome type "escalated" to CustomerSupportOutcomeEvaluationResult enum in `app/domains/customer_service/services/support/outcome/customer_support_outcome_evaluation.py`. Add evaluation logic: if reason_code contains "insufficient_confidence" or "missing_context", return ESCALATED result.
- [ ] **Human correction tracking:** Add field `human_corrected_by: UUID | None` to CustomerSupportOutcomeEvaluationRecord in `app/domains/customer_service/models/outcomes.py`. Add enum value "human_corrected" to CustomerSupportOutcomeEvaluationResult. Update evaluation service to check if human modified any operations and set this flag.
- [ ] **Customer reopening signal:** Add model CustomerSupportOutcomeReopeningRecord in `app/domains/customer_service/models/outcomes.py` with fields: outcome_id (FK), reopened_by_customer_at (timestamp), reason_text, customer_message. Add service method `record_reopening()` to CustomerSupportOutcomeRecordingService and emit SUPPORT_OUTCOME_REOPENED_EVENT.
- [ ] **Action failure vs. resolution failure:** Enhance evaluation to distinguish: add "action_failed_but_escalated" result type, and track in evaluation whether customer accepted the outcome (via conversation sentiment or explicit feedback). Document this distinction in reason_code.
- [ ] **Outcome status enum:** Replace CustomerSupportOutcomeRecord.status String(32) with Enum field using StrEnum (REJECTED, PREPARED, SUBMITTED, COMPLETED, FAILED, UNKNOWN). Update evaluation logic to validate only legal status transitions.
- [ ] **Broader outcome coverage:** Add generic AIInteractionOutcome record for non-refund conversations (e.g., agent suggestions that are sent). Create in `app/domains/customer_service/models/outcomes.py` with fields: conversation_id, interaction_type (suggestion/automation/manual), outcome_type, result. Emit outcomes for all high-impact interactions, not just support reviews.
- [ ] **Policy conflict outcome:** Add "policy_conflict" to CustomerSupportOutcomeEvaluationResult enum. Update evaluator to detect when decision is "rejected" due to policy constraints and set result accordingly.
- [ ] **Comprehensive evaluation:** Extend CustomerSupportOutcomeEvaluator to handle escalations, agent suggestions, and non-refund interactions. Add test in `tests/customer_service/objectives/test_customer_support_comprehensive_outcome_evaluation.py` covering: success, partial success, escalation, human correction, customer reopening, policy conflict, action failure scenarios. 
