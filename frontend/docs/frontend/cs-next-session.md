# Customer service: next session handoff

Written 2026-09-30, updated 2026-10-01 (twice; the second update covers the Desk rebuild). This replaces `automation-next-jobs.md` as the current plan
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
- The AI provider (OpenAI) works; the owner set a $2 spend limit on 2026-10-01. The app uses `gpt-4.1-mini` (cheap). If chat replies turn into the standby message, check credits first.
- Test orders in the Shopify dev store (`tajeran-support-dev`), all marked test, example.com emails: #1006 Anna Keller `anna.keller.test@example.com` (paid, unfulfilled), #1007 Ben Ortiz `ben.ortiz.test@example.com` (paid, fulfilled, no tracking), #1008 Clara Voss `clara.voss.test@example.com` (payment pending). Old order #1001 has no email, so chat never shares it (see order protection below).
- Publishing a workflow version from an agent session needs the owner's explicit yes each time.

Owner rules: only real backend data in the app (no fixtures); never restart shared Docker services (postgres, redis) without asking; **never delete data or workflows without asking**; cancellations, refunds and damaged-item requests stay human-only (hard-coded in `backend/app/api/products/customer_service/channels.py`, `safe_handoff_intents`).

---

## 2. What exists (built and tested)

Spec: `backend/.claude/features/cs-frontend-spec.md`. Audit: `backend/.claude/features/cs-frontend-audit.md`.

| Area | Where |
|---|---|
| Automations: list, graph editor, Ask TCOS proposals, Refine, test on past conversations (dry run), publish, version history, Needs review, run review | `frontend/src/domains/customer-service/automation/*`; backend `services/automation_studio.py`, routes `api/products/customer_service/studio.py` (`/customer-service/studio/*`) |
| Live (Now + Activity log), menu item **Live** → `/app/live` | `frontend/src/domains/customer-service/live/*`; backend `services/live_monitor.py`. Activity is job-based: one row per customer message (the worker retries a job; each attempt is a separate run). Old developer run list still at `/app/runs`, not in the menu. |
| Desk: four tabs (**Automation**, **Tickets**, **Speed**, **Satisfaction**), one working filter (Time: 7 / 30 / 90 days). Everything comes from one request; the page fetches it once and passes it to the tab. | Page `src/app/(app)/app/dashboard/page.tsx`; reports `frontend/src/domains/customer-service/desk/DeskReports.tsx`; backend `services/desk_insights.py` (`GET /studio/desk/insights?days=`, sections `automation`, `tickets`, `speed`, `rating`, each with a `_previous` where a comparison exists) |
| Chat widget 👍/👎 on latest answer + one-time 1–5 rating | `frontend/public/tajeran-chat-widget.js`; backend `services/customer_feedback.py`, public routes in `channels.py`. 👎 creates a `run_flag` quality review → shows in Needs review. Ratings use `cs_csat_surveys`. |
| Inbox: topic label + topic filter; run entries show "Workflow · vN", honest "Handed to your team", "Needs a person" case state, link to run review | `inbox/components/list/InboxQueue.tsx`, `inbox/case/*`, `model/topics.ts`; topic = latest `cs_conversation_insights.intent` |
| Settings tabs: Workspace + **Connections** (Channels moved here; `/app/channels` redirects) | `src/app/(app)/app/settings/connections/page.tsx`, `domains/customer-service/channels/ConnectionsScreen.tsx`, `domains/workspace/SettingsTabs.tsx` |
| Knowledge search step fixed (searches the customer's message by default) | `backend/app/runtime/nodes/builtins/knowledge_search.py` |
| Ask TCOS briefing: real config keys for every library step; prompts may only use `{{input}}` / `{{vars.key}}`; validation blocks `{{#each}}`-style templates | `automation_studio.py` (`PROPOSAL_SYSTEM`, `_generate`, `_validate`) |
| Three sample help articles ("Shipping policy (sample)", "Returns and refunds (sample)", "Gift wrapping (sample)") | Created via `POST /api/customer-service/knowledge/sources/inline`. The owner will replace them with real policies. |

Dev workspace workflow state: "Website chat automation" (`15aad0a7-0217-4162-ad96-cce74340aa92`) is **live on v22** (2026-10-01). Graph: trigger → Remember the conversation → Find order number → Search knowledge → route → (Find order → order reply | general reply) → Reply in chat. All older drafts are discarded.

Built on 2026-10-01 (all verified live through the public chat API, 14/14 correct team flags on v22):

| Behaviour | Where |
|---|---|
| Standby reply on the first AI-provider failure (no job retries) | `backend/app/runtime/nodes/builtins/llm_generate.py` |
| Knowledge search falls back to keyword results when embeddings fail | `backend/app/services/knowledge_retrieval.py` |
| Dead-lettered chat run sends one safe "team will reply" message (idempotent per job) | `send_customer_chat_safe_reply_on_dead_letter` in `backend/app/domains/customer_service/events/handlers.py`. The inbox shows such a case as "Action failed". |
| Hand-off marker: a reply that ends with `[HANDOFF]` is sent without the marker and the run gets `meta.handoff_required` → "Needs a person" in the Inbox, "Waiting for a person" in Live (shown at once, no one-minute grace) | `runtime/nodes/customer_chat.py`; the prompts in the workflow carry the hand-off rule; `PROPOSAL_SYSTEM` tells Ask TCOS about it |
| Order protection: chat shares an order only if the chat's email, or an email typed in the conversation, matches the order's email. No email on the order → "a team member will check" + flag | `_chat_order_refusal` in `backend/app/providers/shopify/runtime/nodes.py`; the chat event payload now carries `customer_email` |
| Conversation memory: step `customer_service.load_conversation` ("Remember the conversation") puts recent messages in `vars.conversation` (bounded by `CustomerServiceAIContextPolicy`) and the last order number in `vars.conversation_order_ref`, which "Find order number" falls back to | `runtime/nodes/conversation_history.py`, `order_ref.py`. Empty in "Test on past conversations" (dry run has no conversation). |
| Bot stays quiet once a team member has replied, until the ticket is resolved (`dispatch_skip_reason = team_member_is_handling`) | `backend/app/api/products/customer_service/channels.py` |
| General return/refund questions with no order number ("How do I return…", "What is your return policy?") go to the help articles; "I want a refund" still starts the order-number intake and the approval flow | `_is_policy_question` in `services/support/customer_support_orchestration.py` |
| Team notification: count badge on **Live** in the menu + pop-up "X needs a person" on any screen (polls every 15 s) | `frontend/src/domains/customer-service/live/useWaitingForPerson.ts`, `HandoffNotice.tsx`, `ui/layout/AppRail.tsx`, `AppShell.tsx` |
| Draft test results record `draft_handed_over` per case (not shown in the UI yet) | `automation_studio.py` |

Owner decisions on 2026-10-01: a person keeps the final say on refunds (Approvals), cancellations and damaged items (straight to the team), returns and billing worries (bot explains, then hands over). A paid but unshipped order asked about in chat is flagged for the team to ship; if that gets noisy, limit it (e.g. orders older than two days).

Built in the second 2026-10-01 session (Desk and chat fix committed as `f68023f3`; the chat widget rows are **not committed yet**, ask the owner):

| Behaviour | Where |
|---|---|
| Speed tab with real timings: first reply = first bot or team message after the customer's first message; resolve time = `resolved_at - created_at`; medians and time buckets; empty states where there is no data | `_speed` in `desk_insights.py`, `SpeedReport` |
| Tickets tab: new / open / pending / resolved counts, real age of the oldest open ticket, backlog age chart (from `created_at`), tickets by channel (stored value is `website`), automation rate tile | `_tickets` in `desk_insights.py`, `TicketsReport` |
| Removed from the Desk: Unsolved tickets, Assignee activity, Agent updates, Backlog (merged into Tickets), SLAs (returns with Task 7), the Share / Schedule / Export buttons, the Channel / Team / Priority / Customer filters, the "Latest tickets" table (same list as the Inbox). "No earlier data to compare." shows once, under the tabs | `dashboard/page.tsx` |
| Resolving a ticket now saves `resolved_at` (it never did before). The "bot stays quiet until the ticket is resolved" rule reads the same field, so it only works for tickets resolved after this fix | `repositories/tickets.py` (`update`), `services/helpdesk.py` (bulk status) |
| Chat no longer goes down when an email matches duplicate customers: the session links to the newest matching customer and logs a warning with the duplicate ids | `ensure_inbox_bridge_for_session` in `services/chat_service.py` |
| Settings → **Chat widget** tab: on/off, install code, title, assistant name, colour, position, greeting, and three self-service switches stored in the widget settings under `meta.self_service` (`track_order`, `report_problem`, `start_return`). `/app/chatbot` redirects here; Connections links here. The tab saves only its own fields, so the attached workflow and auto-answer settings are untouched | `src/app/(app)/app/settings/chat-widget/page.tsx`, `domains/customer-service/chatbot/ChatWidgetScreen.tsx`, `domains/workspace/SettingsTabs.tsx` |
| Widget self-service buttons (shown above the message box when switched on). **Track my order**: order number + email → status and tracking link straight from Shopify, no AI; the answer is shown only in the chat window, not saved to the conversation. **Report a problem** / **Start a return**: order number + description → saved as a customer message plus a "passed to our team" reply; no automation runs, and it appears in Live → Now after the usual one-minute grace | `frontend/public/tajeran-chat-widget.js`; `POST /chat/public/{key}/sessions/{id}/track-order` and `/requests` in `backend/app/api/products/customer_service/channels.py`; public settings return `self_service` |
| Order lookup protection: `track-order` answers only when the order number and the order's email both match; a wrong number, a wrong email and an order with no email all return the same "not found" | `track_order` in `channels.py` (verified with #1006, #1007, #1001 and an unknown number) |

Work up to v22 is committed on branch `feature/cs-automation-live-desk` (not pushed).

---

## 3. Tasks, in order

### Task 0: DONE (superseded by v22, see section 2)

Original task: Publish v13 and verify live
1. Open `/app/workflows/proposals/b2fc51a0-0665-4bb8-af3a-13f487ad632e`, run "Test again", publish v13.
2. Send real messages through the public chat API: "Do you ship to Canada?", "Do you ship to Australia?", "Do you offer gift wrapping?", "Where is my order #1001?", "I want a refund for order #1001".
3. Confirm each answer is correct and comes from the articles or Shopify (no invented facts), `platform_jobs.payload.extras.workflow_version = 13`, and the runs show correctly in Live → Activity log, the Inbox timeline and Desk.
4. If anything fails live, restore v1 immediately (`POST /studio/workflows/{id}/versions/1/restore`) and report.

Done when: live customers get article-based answers on v13.

### Task 1: DONE (work is committed on `feature/cs-automation-live-desk`; still ask before every commit)

Original task: Ask the owner about git
Ask whether to commit (and on which branch; current branch is `main`, so propose a feature branch). Don't commit without a yes. Use the attribution lines from the system reminder.

### Task 2: DONE (see section 2)

Original task: Customer gets no reply when a run fails completely
When a `workflow.run` job dead-letters (every attempt failed), the customer gets nothing. Send one safe message ("Thanks for your message. A member of our team will get back to you shortly.") into the chat and inbox, once per failed job, idempotently. Find where jobs are dead-lettered (`backend/app/platform/jobs/`) and where the reply node sends chat messages (`reply.customer_chat`). Prefer a product-layer hook over changing the core job engine. Make sure Live → Now still shows the conversation as waiting for a person.

Done when: a forced failure (e.g. a draft with a broken step published to a test workflow, then restored) leaves the customer with the safe message and the case marked "Needs a person".

### Task 3: DONE (see section 2; not yet exercised live with the provider really down)

Original task: Stop 3× retries on AI provider failure
When the AI provider fails, the worker retries the whole job 3 times (about 27 s before the standby reply). `llm.generate` has `provider_failure_fallback`; find why the job still fails/retries (check how `LLMProviderError` / circuit-open is raised and how the job decides to retry). Goal: the standby reply goes out on the first failure, no job retry for provider outages.

Done when: with the provider simulated down (in a test, not by breaking the real key), the customer gets the standby reply within a few seconds and the job has 1 attempt.

### Task 4: DONE (see section 2: Time works, the other filters were removed)

Original task: Desk filter buttons do nothing
`src/app/(app)/app/dashboard/page.tsx` has "Time / Channel / Team / Priority / Customer" buttons and a hard-coded "Last 30 days". Either make Time work (7 / 30 / 90 days, passed to the Automation and Satisfaction reports and the ticket data) or remove the buttons that can't work yet. Ask the owner which buttons to keep before building more than Time.

### Task 5: DONE for the outage (see section 2). Still open: **ask the owner** whether to merge the 24 duplicate `john@example.com` customers.

Original task: Chat widget down for duplicate customers
`john@example.com` matches 24 duplicate `cs_customers` rows in the dev workspace, so `CustomerIdentityService` raises `CustomerIdentityConflictError`, session creation returns 500, and the widget shows "Chat is temporarily unavailable".
- **Ask the owner** before merging or deleting any customer rows.
- Regardless: chat must not go down on an identity conflict. Degrade gracefully (e.g. start the session linked to the most recent matching customer or an unlinked one, and log the conflict for review). Keep the change in the chat/session product layer.

### Task 6: DONE (see section 2)

Original task: Settings → Chat widget tab + self-service buttons
- Add a third Settings tab "Chat widget" that replaces the hidden `/app/chatbot` page (install code, look, greeting; reuse the existing chatbot components/settings API) and link to it from Connections.
- Add switches for self-service buttons shown when the chat opens: **Track my order**, **Report a problem**, **Start a return**.
- In the widget: "Track my order" asks for the order number (and email if needed) and shows status + tracking link from Shopify data directly (no AI). "Report a problem" and "Start a return" collect the order number and a short description, then hand to the team (human-only rule).
- Check the order lookup can't be used to read someone else's order (require order number + matching email).

### Task 7: NEXT. Reply-time targets + business hours
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
- The old chatbot page's controls for the attached workflow, minimum confidence and hand-off message are no longer in the UI (the values are kept). `chatbot/components/ChatbotHero.tsx`, `StorefrontPreviewPanel.tsx` and `ChatbotUi.tsx` are now unused.
- A self-service request shows in Live with the reason "No automation answered this message." A clearer reason would need its own marker.
- `public/widget-test.html` has no viewport meta tag, so the widget looks tiny at 375px on that page only.
- The bot answered a bare "1006" with the gift-wrapping article (conversation memory carried the earlier question).
- The dev workspace has all three self-service switches turned on (set during testing on 2026-10-01).
- The 7 tickets resolved before the `resolved_at` fix have no resolve time (the owner has not approved filling it in from `updated_at`), so they are missing from "Time to resolve" and "Resolved", and the bot stays quiet on any of them where a team member replied. One test ticket (`e40ba45e-36c7-40ac-aae0-354c848c06d3`, "John Duplicate Test") was resolved on 2026-10-01 to verify the fix.
- `/app/operations` still uses `analytics()`, `workloadReport()`, `slaViolations()` and `auditLogs()`; the Desk no longer does.
- Desk "Open" and "Pending" are the queue right now; the Time choice applies to new, resolved, speed, automation and ratings.
- Duplicate-message timestamps: the workflow job is created a few ms before the triggering message is saved (the inbox timeline compensates).
- `backend/app/domains/customer_service/repositories/workflow_executions.py` `list_for_user` loads the last 100 workspace jobs and filters by conversation in Python, so old conversations can lose their runs on a busy store.
- `frontend/src/ui/layout/AppSidebar.tsx` and the old `domains/customer-service/channels/components/*` are unused.
- Some `cs_chat_messages.meta` values are JSON `null`; merge into meta with `CASE WHEN jsonb_typeof(meta)='object' ...`, never `coalesce(meta,'{}') || ...`.
- Draft test results know which replies would be handed to the team (`draft_handed_over`), but the proposal screen doesn't show it.
- The order reply can't see the shipping country, so it may quote US delivery times to a Canadian order.
- The Inbox side panel attaches an order the customer merely mentions to that customer (agent-facing only).
- Six chat tests under `backend/tests/customer_service/chat` and 30 under `tests/customer_service` (objective/learning routers) fail with 403 on the baseline too.
