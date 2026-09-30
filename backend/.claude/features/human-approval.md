# Feature: Human Approval

## Spec
- **What it should do:** Pause an operation, request approval from an authorized human, and safely continue or cancel based on the decision.
- **Layer:** core (runtime pause/resume) + product (approval UI)
- **Likely location (guess — verify, I don't have your repo):** app/runtime approval/wait state + domains/customer_service approval queue UI
- **Key entities:** Approval Request, Approval Decision, Approver, Action, Conversation, Workflow Run
- **Core rules to check against:** Only authorized users can approve; approval tied to a specific action/context, not reusable; decisions immutable/auditable; runtime must not continue before required approval

## Acceptance criteria (from the v1 spec's "DONE" list)
- Approval can be requested/approved/rejected/cancelled
- Runtime waits correctly; approval is audited
- Action cannot execute without required approval
- Tests cover race conditions and duplicate decisions

## Production success condition
> A sensitive AI action cannot execute until an authorized human explicitly approves it.

## Audit Result
_Filled in by `/audit-feature human-approval`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Runtime human approval node: HumanApprovalNode (app/runtime/nodes/builtins/human_approval.py:11+) with async run() for pause/resume
- Durable wait support: tests verify approval state survives system restarts (test_runtime_human_approval_durable_wait.py)
- Context preservation: approval context linked to conversation/workflow (test_runtime_human_approval_context.py)
- Duplicate approval safety: tests prevent multiple decisions on same request (test_agent_custom_duplicate_approval_safety.py)
- E2E approval flow: endpoint tests for request/approve/reject (test_workflow_human_approval_endpoint_e2e.py)
- Authorization: approval policy enforcement via resolver pipeline (test_resolver_pipeline_approval_policy.py)
- Action blocking: tests verify action cannot execute without approval (implicit in workflow tests)
- Resume support: custom node resume after approval (test_agent_custom_workflow_resume_after_approval.py, test_agent_custom_resume_after_approval.py)
- Audit: approval decisions tracked (implied by tests)

**Is it good enough?**
Mostly. Strengths:
- Runtime pause/wait working
- Durable state preserved
- Duplicate safety tested
- Authorization policy enforced
- E2E flow tested

Gaps vs spec:
- No approval UI/dashboard visible (tests for endpoints but no product-layer approval queue UI)
- Approval request schema/API not explicitly visible in tests (endpoint E2E but no detail on schema)
- Auditability tested but audit log querying not evident
- No explicit test for race conditions (only duplicate decisions)
- Cancellation not explicitly tested

**Gaps / risks:**
1. No approval queue UI: runtime works but no merchant-facing approval dashboard
2. Missing approval API documentation: endpoint exists but schema/params not clear
3. Race condition coverage incomplete: duplicate tested but concurrent decides untested
4. No audit trail querying: decisions tracked but no API to fetch history
5. Cancellation flow missing: can request/approve/reject but cancel not tested

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add approval queue UI: create /approvals dashboard in product layer showing pending requests, allow approve/reject/cancel
- [ ] Document approval API: add schemas/approval.py with ApprovalRequest, ApprovalDecision schemas; document all endpoints
- [ ] Add race condition tests: test_runtime_approval_concurrent_decisions.py covering simultaneous approve/reject
- [ ] Add audit trail API: GET /approvals/{request_id}/history endpoint returning decision audit log
- [ ] Add cancellation support: add cancel() method to HumanApprovalNode; test cancellation prevents resume
- [ ] Add timeout support: add approval_timeout_minutes to HumanApprovalNode; test auto-cancel after timeout
- [ ] Add authorization level enforcement: PATCH /approvals/{request_id}/permissions to set approval requirement (who can approve)
- [ ] Add approval delegation: allow approved user to delegate approval to another authorized user
- [ ] Add notification on approval: call NotificationService when approval requested to notify authorized approvers
- [ ] Add batch approval: POST /approvals/batch-approve for approving multiple related requests 
