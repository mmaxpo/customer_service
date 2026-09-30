# Feature: Basic Workflow

## Spec
- **What it should do:** Create and execute a small workflow (trigger, AI, condition, Shopify action, send message, assign, human approval, wait, end nodes) with coordinated multi-step logic.
- **Layer:** core
- **Likely location (guess — verify, I don't have your repo):** app/tcos DAG workflow engine (workflow builder, node execution, RunState)
- **Key entities:** Workflow, Workflow Version, Workflow Node, Workflow Edge, Workflow Run, Run State, Workflow Event
- **Core rules to check against:** Published workflows are versioned; running workflows retain execution state; invalid workflows cannot be published; side effects controlled/idempotent; tenant isolation applies to every execution; failed runs observable

## Acceptance criteria (from the v1 spec's "DONE" list)
- All v1 node types work; workflow can be created/validated/published/executed
- Wait and approval work; failed runs visible
- Execution state survives interruption; runs are tenant-scoped
- Tests cover representative workflows

## Production success condition
> A merchant can publish and run a real multi-step customer-service workflow and inspect exactly what happened.

## Audit Result
_Filled in by `/audit-feature basic-workflow`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- **DAG execution engine** (`app/runtime/engine/executor.py`) — `execute_workflow_dag()` with 8-step max, node batching (max 8 concurrent), state restoration, error handling, max-steps safety limit
- **Models** (`app/models/models.py`) — `RuntimeWorkflow` (stores name + workflow JSON), `WorkflowRun` (status: running/paused/done/failed, workflow + state JSONB), `WorkflowRunEvent` (event log), `WorkflowDeployment` (versioning metadata)
- **Node types** (`app/runtime/nodes/builtins/`) — trigger.message, response, human.approval (with approval service), wait.time, wait.event, router.rules, router.llm, agent.custom, agent.langgraph, agent.mcp, join.all, set.variable, subworkflow.call, control.loop, llm.generate, knowledge.search, platform.job.enqueue, capability.invoke, web.search, context.extract
- **State management** (`app/runtime/state/run_state.py`) — new_run_state(), finish_run_state(), support for resumption from paused state
- **Workflow validation** (`app/runtime/engine/validator.py`) — validate_workflow() called before execution
- **Events & observability** — WorkflowRunEvent model + streaming API (`/runs/{id}/stream`) for real-time event consumption
- **Approval workflows** (`app/workflow_operations/waits/`) — WorkflowWaitService for durable wait tracking
- **Tests** — approval workflow tests, wait node tests, resume tests, tenant isolation tests, failure handling tests

**Is it good enough?**
- **Mostly yes, with caveats.** All v1 node types exist and execute; pause/resume works; events are tracked. But:
  - ✓ v1 intents supported (trigger, AI, condition, action, message, assign(?), approval, wait)
  - ✓ Workflows created/validated/executed
  - ✓ Approval and wait nodes work
  - ✓ Failed runs visible in event log
  - ✓ Execution state survives interruption
  - ✓ Tests cover representative workflows
  - ✓ Tenant isolation enforced at API layer (user_id check in stream endpoint)
  - ⚠️ **Missing:** no "publish" endpoint to version/release workflows; WorkflowDeployment model exists but no API to create deployments
  - ⚠️ **Unclear:** "send message" node not found; "assign" node not found (only assign-related fields in data structures)
  - ⚠️ **Unclear:** Idempotency policy for side-effect nodes (platform.job.enqueue, knowledge.ingest) — replay_policy="skip" exists but not clear if all paths use it
  - ⚠️ **Risk:** Workflow validation might not catch all invalid workflows; no schema version check

**Gaps / risks:**
- **Workflow publish API missing:** WorkflowDeployment schema exists (id, workflow_key, workflow_version_id, environment, deployed_by, metadata) but no POST /workflows/publish or similar endpoint to create deployments and version workflows. Feature is publishable but publish workflow unclear.
- **Send message node:** Feature spec mentions "send message" as a v1 node type, but grep finds no node type registered or implementation for it. May be via platform.job or a product-specific node.
- **Assign node:** Feature mentions "assign" (likely for routing/assignment in customer service), but no assign node found in registry. Searching finds "assignment" in conversation models but not a workflow node.
- **Idempotency verification:** Replay safety exists (skip_replay_blocked_nodes, replay_policy="skip") but not all side-effect paths explicitly confirmed to be idempotent. Risk: resuming a workflow might re-execute an action that should only run once.
- **Workflow validation completeness:** Validator checks existence of nodes/edges but may not check for deadlocks, unreachable nodes, invalid transitions. No acceptance criteria test in acceptance criteria.
- **Tenant isolation breadth:** Checked in API stream endpoint but need to verify all paths (event_sink, run_store, node execution contexts) enforce workspace/tenant boundaries.
- **State persistence under failure:** State survives pause but unclear if state survives catastrophic failures (OOM, process crash) — run_store persists but rollback/recovery path unclear.

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] **Workflow publish API:** Add POST `/workflows_route/runtime/{workflow_id}/publish` endpoint to `app/api/workflows.py` that: (1) validates workflow, (2) creates WorkflowDeployment record, (3) increments version, (4) returns published_workflow_id + version. Add corresponding `publish()` method to PostgresWorkflowRepo.
- [ ] **Send message node:** Verify spec intent (is it Shopify send message, email send, or generic?). If v1 feature, add `send.message` node to `app/runtime/nodes/builtins/` with implementation + registry entry. If not v1, note in spec that it's out of scope.
- [ ] **Assign node:** If v1 feature, clarify scope (assign to queue, agent, automation?) and add `assign.node` to `app/runtime/nodes/builtins/` + registry. If product-specific, move to customer_service domain.
- [ ] **Idempotency audit:** Grep `app/runtime/nodes/builtins/` for side_effect=True nodes and verify each has replay_policy="skip" or equivalent re-execution guard. Add retry logic with idempotency key to platform.job.enqueue if missing.
- [ ] **Workflow validation enhancement:** Add checks to `app/runtime/engine/validator.py` for: (1) no unreachable nodes (orphaned DAG), (2) no invalid router transitions, (3) all referenced variables bound. Add acceptance test in `tests/runtime/test_workflow_comprehensive_validation.py`.
- [ ] **Tenant isolation comprehensive:** Add test in `tests/api/test_workflow_tenant_isolation_comprehensive.py` that verifies: (1) stream endpoint user_id check, (2) run_store filters by user_id, (3) event_sink filters by user_id, (4) node execution contexts do not cross workspaces.
- [ ] **State persistence under crash:** Verify WorkflowRun state + events are persisted transactionally before node execution. Add test `tests/runtime/test_workflow_crash_recovery.py` simulating process failure and resumption.
- [ ] **Workflow versioning strategy:** Document in code or CLAUDE.md: when workflow is published, how versions are tracked (integer, semver, commit hash?), and how running workflows reference a specific version vs. always using latest. 
