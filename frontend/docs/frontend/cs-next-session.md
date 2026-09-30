# Customer service: next session handoff

Written 2026-09-30. This replaces `automation-next-jobs.md` as the current plan
(that file is kept for history). Read this whole file before starting.

Work **one task at a time**. For each task: inspect the code, build the
smallest solution, run it, check it in the real app with real data (desktop
and 375px), report, and **wait for the owner's approval** before the next task.
Follow `frontend/CLAUDE.md`.

---

## 1. Environment (read first)

| Piece | How it runs | Notes |
|---|---|---|
| Frontend | Docker container `frontend-dev` on `:3000`, mounts `frontend/` | Typecheck: `docker exec frontend-dev sh -c "cd /app; npx tsc --noEmit -p ."`. No ESLint config. |
| Backend API | `uv run uvicorn app.main:app --reload` on `:8000` (owner's terminal) | Auto-reloads on file changes. |
| Job worker | `uv run python -m app.platform.jobs` (owner's terminal) | **Does NOT auto-reload.** Live chat runs execute here; proposal "Test on past conversations" runs in the API. After changing `backend/app/runtime/**` or anything a workflow run executes, ask the owner to restart the worker. The owner restarted it at 17:05 on 2026-09-30, so it has all fixes so far. |
| DB | `docker exec postgres-dev psql -U postgres -d postgres` | Huge amounts of test data: always filter by workspace. |
| Browser | Claude browser pane; the owner logs in there | Sessions now refresh automatically (`/api/auth/refresh`). A raw `fetch` from `javascript_tool` does not refresh: call `POST /api/auth/refresh` first. Coordinate clicks from the browser tool sometimes miss; verify with a screenshot. |

- Dev workspace id: `14363957-27b0-49d0-ad88-4ee60476bc02`. Customer-service data is keyed by workspace id in `user_id` columns; CS routes use `get_customer_service_principal` whose `.id` is the workspace id.
- Backend scripts: run from `backend/` with `PYTHONPATH=. .venv/bin/python script.py` (put scripts in the session scratchpad, not the repo).
- Chat widget test page: `http://localhost:3000/widget-test.html` (public key `cw_3ff5789a728f47e7831b809382be7ac8`). It hard-codes `john@example.com`, which currently breaks (see task 5). To chat as a clean customer, send messages to the public API instead:
  - `POST /customer-service/chat/public/{key}/sessions` with `{"visitor_id": "...", "customer_name": "...", "customer_email": "..."}`
  - `POST .../sessions/{session_id}/messages` with `{"content": "..."}`
  - `GET .../sessions/{session_id}/messages`
  - An existing clean test session: `4f402816-3bff-449a-ba7a-5a74ffb2514c` ("Studio Test Customer", conversation `0e7425ed-43ad-4c4e-8d21-cd3093388ea3`).
- The AI provider (OpenAI) works again as of 2026-09-30.

Owner rules: only real backend data in the app (no fixtures); never restart shared Docker services (postgres, redis) without asking; **never delete data or workflows without asking**; cancellations, refunds and damaged-item requests stay human-only (hard-coded in `backend/app/api/products/customer_service/channels.py`, `safe_handoff_intents`).

---

## 2. What exists (built and tested)

Spec: `backend/.claude/features/cs-frontend-spec.md`. Audit: `backend/.claude/features/cs-frontend-audit.md`.

| Area | Where |
|---|---|
| Automations: list, graph editor, Ask TCOS proposals, Refine, test on past conversations (dry run), publish, version history, Needs review, run review | `frontend/src/domains/customer-service/automation/*`; backend `services/automation_studio.py`, routes `api/products/customer_service/studio.py` (`/customer-service/studio/*`) |
| Live (Now + Activity log), menu item **Live** → `/app/live` | `frontend/src/domains/customer-service/live/*`; backend `services/live_monitor.py`. Activity is job-based: one row per customer message (the worker retries a job; each attempt is a separate run). Old developer run list still at `/app/runs`, not in the menu. |
| Desk: new **Automation** tab (default) and real **Satisfaction** tab | `frontend/src/domains/customer-service/desk/DeskReports.tsx`; backend `services/desk_insights.py` (`GET /studio/desk/insights?days=`) |
| Chat widget 👍/👎 on latest answer + one-time 1–5 rating | `frontend/public/tajeran-chat-widget.js`; backend `services/customer_feedback.py`, public routes in `channels.py`. 👎 creates a `run_flag` quality review → shows in Needs review. Ratings use `cs_csat_surveys`. |
| Inbox: topic label + topic filter; run entries show "Workflow · vN", honest "Handed to your team", "Needs a person" case state, link to run review | `inbox/components/list/InboxQueue.tsx`, `inbox/case/*`, `model/topics.ts`; topic = latest `cs_conversation_insights.intent` |
| Settings tabs: Workspace + **Connections** (Channels moved here; `/app/channels` redirects) | `src/app/(app)/app/settings/connections/page.tsx`, `domains/customer-service/channels/ConnectionsScreen.tsx`, `domains/workspace/SettingsTabs.tsx` |
| Knowledge search step fixed (searches the customer's message by default) | `backend/app/runtime/nodes/builtins/knowledge_search.py` |
| Ask TCOS briefing: real config keys for every library step; prompts may only use `{{input}}` / `{{vars.key}}`; validation blocks `{{#each}}`-style templates | `automation_studio.py` (`PROPOSAL_SYSTEM`, `_generate`, `_validate`) |
| Three sample help articles ("Shipping policy (sample)", "Returns and refunds (sample)", "Gift wrapping (sample)") | Created via `POST /api/customer-service/knowledge/sources/inline`. The owner will replace them with real policies. |

Dev workspace workflow state: "Website chat automation" (`15aad0a7-0217-4162-ad96-cce74340aa92`) is **live on v1**. Test versions v8, v10, v12 are in its history (leave them). **v13 is a draft proposal** (`b2fc51a0-0665-4bb8-af3a-13f487ad632e`) that adds a knowledge search before general replies; it passed 5/5 tests with the real AI.

**Nothing is committed to git yet** (~43 changed/new files across `frontend/` and `backend/`, all from this work).

---

## 3. Tasks, in order

### Task 0: Publish v13 and verify live (worker already restarted)
1. Open `/app/workflows/proposals/b2fc51a0-0665-4bb8-af3a-13f487ad632e`, run "Test again", publish v13.
2. Send real messages through the public chat API: "Do you ship to Canada?", "Do you ship to Australia?", "Do you offer gift wrapping?", "Where is my order #1001?", "I want a refund for order #1001".
3. Confirm each answer is correct and comes from the articles or Shopify (no invented facts), `platform_jobs.payload.extras.workflow_version = 13`, and the runs show correctly in Live → Activity log, the Inbox timeline and Desk.
4. If anything fails live, restore v1 immediately (`POST /studio/workflows/{id}/versions/1/restore`) and report.

Done when: live customers get article-based answers on v13.

### Task 1: Ask the owner about git
Ask whether to commit (and on which branch; current branch is `main`, so propose a feature branch). Don't commit without a yes. Use the attribution lines from the system reminder.

### Task 2: Customer gets no reply when a run fails completely
When a `workflow.run` job dead-letters (every attempt failed), the customer gets nothing. Send one safe message ("Thanks for your message. A member of our team will get back to you shortly.") into the chat and inbox, once per failed job, idempotently. Find where jobs are dead-lettered (`backend/app/platform/jobs/`) and where the reply node sends chat messages (`reply.customer_chat`). Prefer a product-layer hook over changing the core job engine. Make sure Live → Now still shows the conversation as waiting for a person.

Done when: a forced failure (e.g. a draft with a broken step published to a test workflow, then restored) leaves the customer with the safe message and the case marked "Needs a person".

### Task 3: Stop 3× retries on AI provider failure
When the AI provider fails, the worker retries the whole job 3 times (about 27 s before the standby reply). `llm.generate` has `provider_failure_fallback`; find why the job still fails/retries (check how `LLMProviderError` / circuit-open is raised and how the job decides to retry). Goal: the standby reply goes out on the first failure, no job retry for provider outages.

Done when: with the provider simulated down (in a test, not by breaking the real key), the customer gets the standby reply within a few seconds and the job has 1 attempt.

### Task 4: Desk filter buttons do nothing
`src/app/(app)/app/dashboard/page.tsx` has "Time / Channel / Team / Priority / Customer" buttons and a hard-coded "Last 30 days". Either make Time work (7 / 30 / 90 days, passed to the Automation and Satisfaction reports and the ticket data) or remove the buttons that can't work yet. Ask the owner which buttons to keep before building more than Time.

### Task 5: Chat widget down for duplicate customers
`john@example.com` matches 24 duplicate `cs_customers` rows in the dev workspace, so `CustomerIdentityService` raises `CustomerIdentityConflictError`, session creation returns 500, and the widget shows "Chat is temporarily unavailable".
- **Ask the owner** before merging or deleting any customer rows.
- Regardless: chat must not go down on an identity conflict. Degrade gracefully (e.g. start the session linked to the most recent matching customer or an unlinked one, and log the conflict for review). Keep the change in the chat/session product layer.

### Task 6: Settings → Chat widget tab + self-service buttons
- Add a third Settings tab "Chat widget" that replaces the hidden `/app/chatbot` page (install code, look, greeting; reuse the existing chatbot components/settings API) and link to it from Connections.
- Add switches for self-service buttons shown when the chat opens: **Track my order**, **Report a problem**, **Start a return**.
- In the widget: "Track my order" asks for the order number (and email if needed) and shows status + tracking link from Shopify data directly (no AI). "Report a problem" and "Start a return" collect the order number and a short description, then hand to the team (human-only rule).
- Check the order lookup can't be used to read someone else's order (require order number + matching email).

### Task 7: Reply-time targets + business hours
Settings → Workspace: "First reply within X, during business hours" plus the weekly schedule (the tab already has a Business hours setting; an SLA backend exists, see `customerServiceApi.slaViolations` and `backend/.claude/features/basic-sla.md`). Show "close to missing the target" in Live → Now, "% answered within target" in Desk, and a small timer on inbox cases near the target.

### Task 8: Sales influenced by support
Desk: "Orders placed within 3 days after a support chat: N · $X" from Shopify order data matched to the chat's customer. Check what order data is stored locally before calling Shopify.

### Task 9: Unanswered-topic suggestions (uses AI)
Cluster customer messages from the last 7 days that no workflow answered (outcome handed over / no workflow). At 3+ in a cluster, show a card above the workflows ("Customers asked about gift wrapping 18 times this week") with Review draft / Dismiss, and "Questions your help articles don't answer" on the Knowledge page. "Review draft" needs Task 10's create-from-prompt, so either do Task 10 first or ask the owner.

### Task 10: Answers in the customer's language (uses AI)
Settings → Workspace: "Reply in the customer's language" + supported languages. `cs_conversation_insights.language` already detects language. In the inbox, show "Customer wrote in German · translated" with a translation for the team.

### Later (ask the owner first)
- Create a brand-new workflow from a prompt. Routing decision needed: how a new workflow gets matched (keywords in `filters.keywords`, a new classifier intent, or an LLM router). A subscription with no filter would catch every message, so it must never ship without one.
- Recommended workflows installed for new workspaces (see Job 1 in `automation-next-jobs.md`).

---

## 4. Known gaps worth remembering
- Duplicate-message timestamps: the workflow job is created a few ms before the triggering message is saved (the inbox timeline compensates).
- `backend/app/domains/customer_service/repositories/workflow_executions.py` `list_for_user` loads the last 100 workspace jobs and filters by conversation in Python, so old conversations can lose their runs on a busy store.
- `frontend/src/ui/layout/AppSidebar.tsx` and the old `domains/customer-service/channels/components/*` are unused.
- Some `cs_chat_messages.meta` values are JSON `null`; merge into meta with `CASE WHEN jsonb_typeof(meta)='object' ...`, never `coalesce(meta,'{}') || ...`.
