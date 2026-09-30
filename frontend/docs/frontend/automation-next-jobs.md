# Automation Studio — next jobs (handoff)

Written 2026-09-30 at the end of the session that built the Automation Studio.
Read this whole file before starting. Work **one job at a time**, report after
each job, and wait for approval before the next one (the owner works in gated
stages).

---

## 1. What exists today

Spec: `backend/.claude/features/cs-frontend-spec.md`.
Phase 0 audit: `backend/.claude/features/cs-frontend-audit.md`. Read the
"Key decisions" section: the TCOS planner is **not** on the live chat path, and a
saved workflow runs directly as an executable graph.

### Screens (left nav → Automations, `/app/workflows`)

| Route | Screen | File (`src/domains/customer-service/automation/`) |
|---|---|---|
| `/app/workflows` | Workflows list: routing strip, Ask TCOS bar, cards, "No match → your team" card | `WorkflowsScreen.tsx` |
| `/app/workflows/review` | Needs-review queue | `ReviewQueueScreen.tsx` |
| `/app/workflows/runs/[runId]` | Review and fix: transcript, run graph, likely cause, flag, propose fix | `RunReviewScreen.tsx` |
| `/app/workflows/proposals/[id]` | Proposal on the graph: summary, refine, diff, checks, test replay, publish | `ProposalScreen.tsx`, `ProposalTestPanel.tsx` |
| `/app/workflows/edit/[workflowId]` | Direct edit: library, "+" on each line, step settings | `WorkflowEditorScreen.tsx`, `StepSettings.tsx`, `graphEdits.ts` |
| `/app/workflows/history/[workflowId]` | Version history and restore | `VersionHistoryScreen.tsx` |
| `/app/workflows/templates` | Old template catalog and builder (the previous Workflows page) | `src/app/(app)/app/workflows/templates/page.tsx` |

Shared pieces: `WorkflowGraph.tsx` (layered graph plus `MiniGraph`),
`AutomationHeader.tsx` (tabs) and `api.ts` (typed client).

### Backend (product layer)

- Service: `backend/app/domains/customer_service/services/automation_studio.py`
- Routes: `backend/app/api/products/customer_service/studio.py`, mounted at
  `/customer-service/studio/*`. Reads need `cs.conversations.read`; changes need
  `cs.automation.manage`.

| Method | Path | Does |
|---|---|---|
| GET | `/studio/workflows` | List workflows with 7-day stats and routing counts |
| GET | `/studio/workflows/{id}` | Raw live graph, for the editor |
| GET | `/studio/workflows/{id}/versions` | Version history |
| POST | `/studio/workflows/{id}/versions/{v}/restore` | Make an earlier version live |
| GET | `/studio/node-library` | Curated step library (Agents / Tools / Logic); Shopify only if connected |
| POST | `/studio/proposals` | `{workflow_id, request}` (LLM) **or** `{workflow_id, workflow}` (graph edit) |
| GET | `/studio/proposals/{id}` | Summary, diff, validation, recent conversations, test results |
| POST | `/studio/proposals/{id}/refine` | Follow-up request (LLM); clears test results |
| POST | `/studio/proposals/{id}/test` | Dry-run replay on past messages with side effects held back |
| POST | `/studio/proposals/{id}/publish` | Needs validation **and** a passing test |
| DELETE | `/studio/proposals/{id}` | Discard |
| GET | `/studio/review` | Runs that failed, handed over, or were flagged (30 days) |
| GET | `/studio/runs/{id}` | Run detail: steps, likely cause, transcript, flags |
| POST | `/studio/runs/{id}/flags` / `/dismiss` | Mark as wrong / "Not a problem" |

Data model decisions (no migrations were added):

- A **workflow** is a `cs_event_subscriptions` row. It is what the dispatcher runs.
- **Versions and proposals** reuse `workflow_definitions` / `workflow_versions`.
  - Each subscription gets one definition; `subscription.meta.definition_id` and
    `meta.live_version` link them.
  - A proposal is a `draft` version with `metadata_json.kind = "proposal"`.
  - Publishing copies the graph onto `subscription.workflow_json`.
- **Flags** are `cs_quality_reviews` rows with `review_type = "run_flag"`.
- The dispatcher stamps `extras.workflow_version` on every `workflow.run` job
  (`services/event_subscriptions.py`).
- **Dry run** calls `execute_workflow_dag(..., replay_state=new_run_state(msg))`
  with no run store.
  - Replay mode skips side-effect nodes (`reply.customer_chat`,
    `shopify.order_action`, …).
  - `DRY_RUN_BLOCKED` also skips capability calls, agents, waits, approvals and
    sub-workflows.

---

## 2. Environment and gotchas (read before testing)

- **Backend**: uvicorn with `--reload` on `:8000` (runs locally, from
  `backend/.venv`). **Job worker**: `python -m app.platform.jobs` must be
  running, or `workflow.run` jobs never execute. Check with `ps aux | grep app.platform.jobs`.
- **Frontend** runs only in Docker: container `frontend-dev` on `:3000`.
  - Typecheck with `docker exec frontend-dev sh -c "cd /app; npx tsc --noEmit -p ."`.
  - The project has no ESLint config.
- **DB**: `docker exec postgres-dev psql -U postgres -d postgres`. This DB also
  holds huge amounts of test data, so always filter by workspace.
- **Dev workspace**: `14363957-27b0-49d0-ad88-4ee60476bc02`. Its owner user is
  `478496b8-…`.
  - Customer-service data is keyed by **workspace id** in `user_id` columns.
  - CS routes use `get_customer_service_principal`, whose `.id` is the
    workspace id.
  - The older `/workflows_route/runs*` APIs scope by the *user* id, so they show
    none of this workspace's runs. Use the studio endpoints instead.
- **Login**: the owner must log in **inside the Claude browser pane**. The pane
  does not share the normal browser's cookies, and it loses the session when the
  app restarts. Never type the owner's real password.
- **OpenAI was rate-limited** all through the last session. LLM steps fail with
  `LLMRateLimitError` / `LLMCircuitOpenError`.
  - "Draft it", "Propose fix", "Refine" and test replay will show "AI provider
    unavailable" until the quota is fixed.
  - Check this first (Job 0).
- The owner's rules: only real backend data in the authenticated app (no
  fixtures); no restarts of shared Docker services (postgres, redis) without
  asking; stop at each job boundary.

---

## 3. Jobs

### Job 0 — Setup check (short)

1. The owner logs in inside the browser pane.
2. Confirm the backend, the worker and `frontend-dev` are up.
3. Confirm the LLM works: create a proposal with Ask TCOS on a harmless request,
   then discard it.
4. If the provider is still failing, report it and continue only with the
   non-LLM parts.

Done when: logged-in screenshots of `/app/workflows` load real data, and the LLM
status is known.

### Job 1 — Default workflows for every workspace

Goal: a new workspace gets useful workflows out of the box, and an admin sees
only their own workspace's workflows.

1. Define two starter packs using the existing system templates
   (`cs_workflow_templates`, `scope = system`; seeds in
   `services/shopify_workflow_catalog.py` and `chatbot_workflow_catalog.py`):
   - **Store (Shopify connected)**:
     - Where is my order (order status)
     - Returns & refunds (with `human.approval` before `shopify.order_action`)
     - Cancel order (with approval)
     - Damaged / wrong item
     - Product questions (`kb.search` + `llm.generate`)
   - **General purpose (no store)**:
     - Answer from knowledge base
     - General AI reply with handoff
2. Add a backend install step. It runs on workspace creation, on Shopify connect
   for the store pack, and on demand from a "Set up recommended workflows"
   empty-state button on `/app/workflows`. It must:
   - create one subscription per workflow, with an **intent filter**
     (`filters.intent` from `CustomerServiceMessageClassifier`) or
     `dispatch_mode`;
   - bootstrap its definition as v1 (reuse `_ensure_definition`);
   - be idempotent, so running it twice creates nothing new.
3. Routing must stay correct: specific intents use `exclusive` with a priority,
   and the general AI reply stays `fallback`. Write down the routing table you
   end up with.
4. The dev workspace has two `TEST …` certification subscriptions. Ask the owner
   whether to hide or delete them. Don't decide alone.
5. Tenant check: a second workspace (test account created on localhost, values
   recorded in a seed or example file) must not see the dev workspace's
   workflows, runs, proposals or versions. Test the studio endpoints directly.

Done when: a fresh workspace shows the right starter pack; the dev workspace list
is clean; cross-workspace reads return 404.

### Job 2 — Message → routing → job → run → reply, traced end to end

Goal: prove how the system handles an incoming message, and make it visible.

1. Send real messages through the public widget:
   `POST /customer-service/channels/chat/public/{public_key}/sessions/{session_id}/messages`.
   Get the key from `cs_chat_widget_settings`. Use one message per intent:
   - order status with an order number
   - refund
   - cancel
   - damaged item
   - general question
   - something unmatched
2. For each message, record the path:
   1. `CustomerSupportOrchestrationService.handle` (claims order/return flows)
   2. the risky-intent handoff in `channels.py`
   3. `enqueue_matching_workflows_for_event` (which subscription won, and why)
   4. the `platform_jobs` row
   5. the worker run (`workflow_runs`, `workflow_run_events`)
   6. the chat reply plus the inbox message
3. Check each run shows correctly in `/app/workflows/runs/{id}`: steps, timings,
   likely cause, transcript and version.
4. Check the refund/cancel paths pause at `human.approval`, appear in
   `/app/approvals`, and only change Shopify after approval, with an idempotency
   key.
5. Write the findings to `backend/.claude/features/cs-routing-trace.md`: a table
   of message → handler → workflow → outcome. Fix only small, clear bugs; list
   bigger ones as tasks.

Known risks to confirm:
- Routing uses a keyword classifier only (5 intents).
- The routing decision is not persisted per conversation.
- `llm.generate` raises on rate limits instead of using its
  `provider_failure_fallback`, so the run fails and the customer gets no reply.
  Confirm this, and fix it if the owner approves.
- Realtime SSE has the `\\n` escape bug in `api/platform.py` (G12).

### Job 3 — Automation panel, full end-to-end UI test

Test on real data in the browser pane at 1440px, 768px and 375px widths, and fix
visual and interaction problems as you find them:

1. **Workflows list**: stats, cards, links, empty state, error state.
2. **Edit steps**:
   1. Insert a step with "+"; change settings; remove a step.
   2. Review changes → proposal. Validation should block an unapproved
      "Change the order" step with a plain message.
3. **Proposal**:
   1. Refine (LLM), then test on past conversations.
   2. Check that the before/after answers make sense.
   3. Confirm publishing is blocked without a passing test.
   4. Publish on a harmless change.
   5. Confirm the next real message runs the new version (check
      `extras.workflow_version` on the job).
4. **Version history**: restore the previous version, then restore forward again.
5. **Needs review**:
   1. Mark an answer as wrong; it shows as flagged.
   2. Propose fix → proposal.
   3. "Not a problem" removes the run from the queue.
6. Keyboard and screen-reader checks: tab order, focus rings, `aria` labels on
   "+" buttons, and status shown in words, not colour alone.

Always restore the dev workspace's live workflows to their original versions when
you finish. The "Website chat automation" subscription is
`15aad0a7-0217-4162-ad96-cce74340aa92`, and its live version is v1.

### Job 4 — Create a new workflow from a prompt

Goal: an admin types "handle gift card balance questions" and TCOS generates a
new workflow they can edit, test and publish.

1. Backend: `POST /studio/workflows` with `{request, name?}`.
   1. The LLM generates a graph from scratch, using the same catalog and prompt
      rules as `_generate`, starting from trigger → response.
   2. Create a private template and a subscription with `is_active = false`.
   3. Return a proposal (v1 draft).
   4. Publishing a proposal for an inactive subscription activates it.
2. **Routing decision (ask the owner first)**: how does a new workflow get
   matched? Options:
   - (a) keywords or phrases generated with the workflow and stored in
     `filters.keywords`;
   - (b) a new intent added to the classifier;
   - (c) an LLM router step.

   A subscription with no filter would catch every message and suppress the
   fallback, so it must never ship without one.
3. Frontend:
   - a "+ New workflow" button in the Workflows header;
   - an Ask TCOS mode switch, "Change a workflow" vs "New workflow";
   - the same proposal screen, showing "New workflow" wording and every step
     marked New.
4. Optional, after 1–3: suggestion cards from unmatched messages. Cluster
   unmatched customer messages from the last 7 days and show a card at 3 or more
   in a cluster. "Review draft" calls the endpoint from step 1 with the examples.

Done when: a prompt-created workflow can be edited, tested, published, receives
matching messages, and doesn't change how other messages are routed.

### Job 5 — Workflows in the inbox

1. The inbox "Run workflow" dialog (`inbox/case/RunWorkflowDialog.tsx` +
   `features/workflow-launcher`) should offer the workspace's studio workflows,
   not the raw templates.
2. Runs started from the inbox must be linked to the conversation (backend gap
   **G1**: `repositories/workflow_executions.py` `_payload_event`), so they show
   in the case timeline and in Needs review.
3. Links in the case timeline (`NextStep.tsx`) should point to
   `/app/workflows/runs/{id}` instead of the old `/app/runs/{id}`, where the run
   belongs to this workspace.
4. Approvals raised by workflows show in `/app/approvals`. Approving resumes the
   run, and the reply appears in the conversation.
5. Handover: when a run hands over (fallback reply, failure), the conversation
   should be clearly marked for a person in the inbox.

Done when: from one conversation you can run a workflow, see its steps, approve
its action, and see the result in the same thread.

---

## 4. Paste-ready prompt for the new session

```
Read /Users/quantum/Desktop/projects/Tajeran.ai/frontend/docs/frontend/automation-next-jobs.md
fully, plus /Users/quantum/Desktop/projects/Tajeran.ai/backend/.claude/features/cs-frontend-spec.md
and cs-frontend-audit.md in the same folder.
Start with Job 0. I'll log in inside the browser pane when you ask.
Work one job at a time: do it, verify it in the real running app with real
data, report, and wait for my approval before the next job. Ask me before
routing decisions (Job 1 step 4, Job 4 step 2) and before deleting anything.
```
