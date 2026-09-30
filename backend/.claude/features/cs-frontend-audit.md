# CS Frontend — Phase 0 capability audit

Spec: `.claude/features/cs-frontend-spec.md` (section 8 checklist, section 9 contracts).
Audited read-only 2026-09-30. Paths relative to `backend/app/`.

## Key decisions (rows 3 and 4 first)

**Row 4: the planner cannot use a saved workflow as a template today.**
The TCOS `PlannerRuntime` / `CognitiveRuntime` is not on the live chat path. Only
`POST /tcos/execute-goal(-runtime)` (`api/tcos.py`) calls it. `PlanningContext`
(`tcos/planner/product_planning/contracts.py`) has `enabled_capabilities` and
`execution_constraints` fields, but nothing reads them. Only
`planner_preferences["learning_advisories"]` is used.
→ **Recommendation for v1:** a saved workflow *is* the executable graph. It runs
directly through `execute_workflow_dag`, which is already how event subscriptions
work. Planner adaptation inside a workflow is deferred. Enforce the allowed
capability list at `capability.invoke` instead.

**Row 3: routing is a keyword classifier plus subscription dispatch.**
`channels.py` public message →
`CustomerSupportOrchestrationService.handle` (claims order/return flows) → else
`CustomerServiceEventSubscriptionService.enqueue_matching_workflows_for_event`.
- The classifier is `workflows/message_classifier.py`: 5 fixed intents with
  hard-coded confidence values between 0.5 and 0.9.
- Dispatch modes live in `subscription.meta.dispatch_mode`
  (standard/exclusive/fallback) plus `dispatch_priority`.
- The decision is only returned in the POST response (`workflow_dispatch`) and
  in `public_ingress` message meta. It is not persisted per conversation.
- Unmatched: nothing runs. The inbox conversation and ticket already exist, so
  there is an implicit human lane, but no summary is created.

## Checklist

| # | Capability | Status | Where / gap → smallest adapter |
|---|---|---|---|
| 1 | Workspace isolation | Partial | The tenant key is `user_id`. A personal workspace id equals the owner's user id (`chat_service.py` `Workspace.id == session.user_id`). CS APIs resolve `principal.workspace_id`. The runtime APIs `/workflows_route/runs*` scope by `current_user.id` and skip the check when `run.user_id` is null (`api/workflows.py` ~151, ~464). → The facade resolves the principal workspace and rejects null-owner rows. |
| 2 | Workflow versions | Partial | There are two systems that are not linked. (a) Core `workflow_definitions`/`workflow_versions` (int version, draft/published, `active_version`, publish/rollback at `/workflow-versions`). (b) CS `CustomerServiceWorkflowTemplate` (mutable, version string) + `CustomerServiceEventSubscription`. Only (b) dispatches. → A subscription references a definition id; dispatch uses its active version. |
| 3 | Router | Partial | See above. → Persist the routing decision and add a "no match" fallback subscription. |
| 4 | Planner template/constraint | Missing | See above. → Run the saved graph directly and enforce allowed capabilities at invoke. |
| 5 | Run pinned to version | Partial | `WorkflowRun.workflow` stores a full JSON copy of the graph. `thread_id` = conversation id for subscription dispatch. No `workflow_version_id`. → Put definition id and version in job `extras`. |
| 6 | Step records | Partial | `node_start`/`node_end` events in `workflow_run_events` (output + meta, timing from `created_at`). Per-node snapshots. No explicit node input. Tokens only on `AgentRun.usage`. |
| 7 | Reasoning summary per step | Missing | → Derive it from node type + output (deterministic). |
| 8 | Live run events | Partial | SSE `GET /workflows_route/runs/{id}/stream` (admin, DB poll, Last-Event-ID) streams raw runtime events. `/realtime/stream` still has the G12 `\\n` bug (`api/platform.py`). No customer stream; public chat polls. Event names differ from the spec (mapping layer needed). |
| 9 | Verifier result | Partial | `tcos/verification` verifies BusinessPlan (TCOS path only). `TaskVerificationRecord` covers capability outcomes. No answer verifier or revise loop on the chat path. |
| 10 | Approval gates | Partial | `HumanApprovalNode` + `WorkflowWait` (`expires_at`, approve/reject/expire-due at `/workflow-waits`). Admin only; no customer approver endpoint. |
| 11 | Idempotent side effects | Partial | Shopify `perform_order_action` uses an advisory lock when an `idempotency_key` is given (optional). `capability.invoke` has none of its own. |
| 12 | Evidence per answer | Missing | `CustomerChatMessage.meta` JSONB is available. → Write the evidence list at answer time. |
| 13 | customer_label | Missing | No field anywhere. → Optional node `data.customer_label` + mapping by node type. |
| 14 | Handover with summary | Partial | `human_handoff_enabled/message` settings are not wired to anything. `ConversationSummaryService` exists. There is no AI pause (see `ai-human-handoff.md`). |
| 15 | NL → workflow patch | Missing | No generation or spec diff. `workflow_operations/diff` compares runs and snapshots. The validator exists (`runtime/engine/validator.py`). |
| 16 | Test replay, side effects mocked | Partial / risk | `/workflow-evaluations/run` enqueues **real** `workflow.run` jobs, so side effects are **not** mocked. Only snapshot replay skips side-effect nodes. |
| 17 | Unmatched clustering | Missing | `workspace_recommendations.py` has a static intent→workflow map only. Unmatched messages are not recorded. |
| 18 | Flags on runs/steps | Partial | `CustomerServiceQualityReview` is per conversation/reply. No run- or step-level flag and no likely-cause hint. |
| 19 | Rules enforced in runtime | Partial | Capability `risk` + binding `requires_approval` + resolver `ApprovalPolicy` + runtime-policy revisions. The Shopify refund/reship durable approval gate. No per-workspace money threshold. |
| 20 | Capability catalog per workspace | Partial | Registry manifests (Shopify) with risk/approval. `/workflows_route/catalog/nodes` and `/capabilities/provider-installations` exist. No combined per-workspace list. |

## Section 9 mapping (summary)

| Spec contract | Existing | Status |
|---|---|---|
| GET /workflows | `/customer-service/automation/event-subscriptions` + templates | facade needed (stats, status) |
| GET /workflows/{id}/versions/{v} | `/workflow-versions/definitions/{id}/versions` | exists (not linked to dispatch) |
| POST .../restore | `/workflow-versions/definitions/{id}/rollback` | exists |
| GET /capabilities | registry + provider-installations | facade needed |
| proposals/* | none | new |
| GET /runs/{id} | `/workflows_route/runs/{id}`, `/events`, `/state`, `/workflows/runs/{id}/timeline` | exists (admin) |
| POST /runs/{id}/flags | quality reviews (conversation-level) | new |
| GET /suggestions | none | new |
| POST /approvals/{id}/decision | `/workflow-waits/{id}/approve|reject` | admin exists, customer missing |
| Live events | `/workflows_route/runs/{id}/stream` | exists, rename in facade |
