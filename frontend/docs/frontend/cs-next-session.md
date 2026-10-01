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
| Job worker | `uv run python -m app.platform.jobs` (owner's terminal). With auto-reload (development only): `uv run watchfiles --filter python "python -m app.platform.jobs" app` from `backend/`; it restarts the worker whenever a Python file under `app/` changes (not yet confirmed on the owner's machine; a restart can interrupt a run that is in progress) | **The plain command does NOT auto-reload.** Live chat runs execute here; proposal "Test on past conversations" runs in the API. After changing `backend/app/runtime/**` or anything a workflow run executes, ask the owner to restart the worker. The owner restarted it at 17:05 on 2026-09-30, so it has all fixes so far. |
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

Dev workspace workflow state: "Website chat automation" (`15aad0a7-0217-4162-ad96-cce74340aa92`) is **live on v23** (2026-10-01; v23 = v22 with the reply prompts' language sentence replaced by `{{vars.reply_language_rule}}`). Graph: trigger → Remember the conversation → Find order number → Search knowledge → route → (Find order → order reply | general reply) → Reply in chat. All older drafts are discarded.

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

Built in the second 2026-10-01 session (Desk and chat fix committed as `f68023f3`; the chat widget as `a8af91bb`; the logo and reply target as `aa6aa0e9`; the sales tile as `87c775e2`; the Inbox translation as `56e90a66`; the language switch and unanswered-topics rows are **not committed yet**, ask the owner):

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
| Chat widget logo: upload in Settings → Chat widget (PNG / JPG / WebP, up to 200 KB), stored as a data URL in the widget settings under `meta.logo`, shown in the chat header instead of "AI" | `ChatWidgetScreen.tsx`, `_logo` in `channels.py`, `tajeran-chat-widget.js`. The file picker itself was not exercised (the agent browser can't choose files); the logo was saved through the API and seen in the tab and the widget. |
| Reply-time target + weekly schedule: Settings → Workspace has "First reply target (minutes)" and, for "Weekly schedule", one opening period per day. Stored in `workspaces.business_hours` (`reply_target_minutes`, `weekly_hours`). The mode value sent is now `scheduled` (the old form sent `weekly`, which the API rejects) | `src/app/(app)/app/settings/page.tsx`; `normalize_working_calendar` and `reply_due_at` in `backend/app/tenancy/working_calendar.py` |
| Target shown in the app: each waiting conversation gets `reply_due_at` and `target_state` (`on_track` / `close` = last quarter of the allowed time / `missed`), counted in business hours from the customer's last message. Live → Now and the Inbox list show "Reply due in X min" or "Reply target missed"; Desk → Speed shows "Answered within target" (first reply by bot or person; unanswered past due counts as late) | `_waiting_for_person` in `live_monitor.py`, `_speed` in `desk_insights.py`, `live/ReplyTargetChip.tsx`, `LiveNowScreen.tsx`, `InboxQueue.tsx`, `DeskReports.tsx` |
| Desk → Automation tile "Orders after a support chat: N · $X": Shopify orders (not cancelled) created within 3 days after a customer message, matched by the customer's email, for the chosen period. Read live from Shopify on each Desk load (about 1.5 s); the tile is hidden when Shopify isn't connected or the call fails. The local `cs_shopify_order_cache` only holds orders someone looked up, so it can't be used for this | `_sales_after_support` in `desk_insights.py`, `list_orders_since` in `services/shopify.py` and `integrations/shopify/real_provider.py`, `AutomationReport` in `DeskReports.tsx` |
| Inbox "Translate conversation" (in the Case activity bar): one AI call translates the last 20 customer, bot and team messages into the workspace language and shows each translation under its message, with "Customer wrote in German · translated" (or "no translation needed"). Nothing is stored. The bot already replies in the customer's language: the v22 prompts end with that rule (checked live with a German question) | `backend/app/domains/customer_service/services/conversation_translation.py`, `POST /studio/conversations/{id}/translate` in `studio.py`, `inbox/case/CaseTimeline.tsx` |
| Language switch (**live on v23 since 2026-10-01**; the text after this still describes how it works): Settings → Chat widget → Language has "Reply in the customer's language" and an optional list of allowed languages, stored in the widget settings under `meta.reply_language`. The "Remember the conversation" step now sets `vars.reply_language_rule` from it. v22's prompts still hard-code "reply in the customer's language", so the switch only takes effect after (1) the worker is restarted and (2) a new version is published whose two reply prompts end with `{{vars.reply_language_rule}}` instead of that sentence. v23 was published with the owner's yes after a worker restart and verified live: German question → German answer; with the switch off → English answer. Two stale drafts (v14, v15) were discarded with the owner's yes | `ChatWidgetScreen.tsx`; `reply_language_rule` in `backend/app/domains/customer_service/runtime/nodes/conversation_history.py` |
| Unanswered-topic suggestions: "Questions your workflows don't answer yet" on Automations and "Questions your help articles don't answer" on Knowledge. One AI call groups the last 7 days of customer messages the automation handed to the team (provider outages excluded); topics with 3+ messages are listed with examples and a Dismiss button. No "Review draft" yet (needs create-from-prompt). The result is cached for 6 hours, with the dismissed topics, in the widget settings under `meta.unanswered_topics` (no new table) | `backend/app/domains/customer_service/services/unanswered_topics.py`, `GET /studio/unanswered-topics`, `POST /studio/unanswered-topics/dismiss`, `automation/UnansweredTopics.tsx`, `WorkflowsScreen.tsx`, `app/knowledge/page.tsx` |
| Live wording fix: a normal bot hand-over was labelled "The AI provider isn't responding…"; it now reads "The automation passed this conversation to your team." Real provider failures keep the old text | `plain_reason` in `live_monitor.py` |

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

### Task 7: DONE (see section 2). Does not use the old SLA policy / violation tables.

Original task: Reply-time targets + business hours
Settings → Workspace: "First reply within X, during business hours" plus the weekly schedule (the tab already has a Business hours setting; an SLA backend exists, see `customerServiceApi.slaViolations` and `backend/.claude/features/basic-sla.md`). Show "close to missing the target" in Live → Now, "% answered within target" in Desk, and a small timer on inbox cases near the target.

### Task 8: DONE (see section 2)

Original task: Sales influenced by support
Desk: "Orders placed within 3 days after a support chat: N · $X" from Shopify order data matched to the chat's customer. Check what order data is stored locally before calling Shopify.

### Task 9: DONE except "Review draft" (see section 2)

Original task: Unanswered-topic suggestions (uses AI)
Cluster customer messages from the last 7 days that no workflow answered (outcome handed over / no workflow). At 3+ in a cluster, show a card above the workflows ("Customers asked about gift wrapping 18 times this week") with Review draft / Dismiss, and "Questions your help articles don't answer" on the Knowledge page. "Review draft" needs Task 10's create-from-prompt, so either do Task 10 first or ask the owner.

### Task 10: DONE except making the switch live (see the "Language switch" row in section 2: needs the open draft resolved, a published v23 and a worker restart).

Original task: Answers in the customer's language (uses AI)
Settings → Workspace: "Reply in the customer's language" + supported languages. `cs_conversation_insights.language` already detects language. In the inbox, show "Customer wrote in German · translated" with a translation for the team.

### New workflow from a prompt: DONE (committed as `e233c620`; keyword editing, delete and the clearer Ask bar as `496a0eb5`)
Replaces "Templates & builder" (link removed; `/app/workflows/templates` and `/builder` redirect to `/app/workflows`).
- Ask bar → "+ New workflow" → TCOS drafts it from a starter graph (`STARTER_WORKFLOW`), names it and proposes keywords and an optional topic. Nothing is saved until **Save**; the draft panel lets the owner edit name, keywords and topic.
- Save creates a `CustomerServiceEventSubscription` with `workflow_json`, `filters.keywords` (required, so it can never catch every message), optional `filters.intent` (general / shipping / refund), `is_active = false`, `meta.source = "studio_prompt"`. The card shows "Runs when a message contains: …" and a Turn on / Turn off link (only for workflows made this way). Steps are edited with the existing "Edit steps" screen.
- A matching non-fallback workflow suppresses the fallback "Website chat automation", so one message gets one answer.
- Code: `draft_workflow`, `create_workflow`, `set_workflow_enabled` in `automation_studio.py`; `POST /studio/workflows/draft`, `POST /studio/workflows`, `POST /studio/workflows/{id}/enabled`; `WorkflowsScreen.tsx`, `automation/api.ts`.
- Verified live: test workflow "Gift Wrap Help" (`5abb161f-e119-44d7-8667-5ccbdc2ff96f`, left switched **off**) answered "Do you offer gift wrapping?" while a shipping question still went to the fallback.
- Cards of prompt-made workflows have "Edit keywords" and, while switched off, "Delete" (asks for confirmation; removes the `cs_event_subscriptions` row). `POST /studio/workflows/{id}/keywords`, `DELETE /studio/workflows/{id}`; both refuse workflows not made from a prompt.
- Adding steps: the step editor inserts one step on a connection (no hand-drawn branches). Branching and several AI steps side by side are done by asking TCOS in words. Checked on 2026-10-01: "three AI steps draft in different ways, then one writes the final reply" produced a valid graph (three `llm.generate` steps feeding a fourth) and passed its test. That draft is still open on "Gift Wrap Help" (proposal `4e50bbfd-b747-47c3-b236-2694de593d13`). Not checked: whether the three steps run at the same time or one after another.
- "Review draft" on each unanswered-topic suggestion drafts a new workflow for that topic (on Automations directly; from Knowledge via `/app/workflows?new=<request>`, which any page can link to). Committed as `93b2c6e3`.
- Inbox → workflow (**not committed yet**): each waiting conversation from `GET /studio/live/now` carries `workflow_gap` (`unanswered` = no workflow ran, `handed_over` = a workflow passed it to the team, else null). In such a conversation the case view shows one line with "Review draft" (`inbox/case/WorkflowSuggestion.tsx`), which opens `/app/workflows?new=…` prefilled from the customer's last message; it is hidden for cancellation, refund and damaged-item topics. The Inbox list has a view "Not answered by a workflow" (also `/app/inbox?view=unanswered`), and the "No match → your team" card links to it. The card's number counts messages in 7 days; the Inbox view lists conversations waiting now, so the two numbers differ.
- Not built: changing the topic after saving.

### Later (ask the owner first)
- Create a brand-new workflow from a prompt. Routing decision needed: how a new workflow gets matched (keywords in `filters.keywords`, a new classifier intent, or an LLM router). A subscription with no filter would catch every message, so it must never ship without one.
- Recommended workflows installed for new workspaces (see Job 1 in `automation-next-jobs.md`).

---

## 3b. Colours and themes (2026-10-01, committed as `9f15a400` except where noted)
- Light theme = "warm neutral" (owner's choice B): page `#efece6`, borders `#d3ccbf`, text `#211e1a`; brand blue and AI purple unchanged. Dark theme (choice D) is a second set of the same tokens under `[data-theme="dark"]` in `src/app/globals.css`.
- Switch: Settings tabs row → "Dark mode / Light mode" (`domains/workspace/ThemeSwitch.tsx`). The choice is kept in the browser (`localStorage` key `tajeran-theme`, applied before first paint by an inline script in `src/app/layout.tsx`) and on the user's account: `GET` / `POST /workspaces/current/theme` read and write `user.ui_theme` with plain SQL (the frontend proxy for `/api/workspaces` has no PUT), and `ThemeSync` in the app layout applies the account's choice on load. Migration `ui01` is applied to the dev database (2026-10-01); other environments need `alembic upgrade head`. `just migrate` / `just current` work from a clean shell since `migrations/env.py` falls back to the app settings (which read `.env.dev` / `.env.prod`) when `DATABASE_URL` is not exported (**not committed yet**).
- Login and the other auth pages already follow the theme (the new `components/marketing/AuthShell` uses the tokens); they have no switch of their own, so they show whatever this browser last used.
- Rule for new UI: use the tokens (`bg-surface`, `bg-background`, `bg-muted`, `border-border`, `text-foreground`, `text-text-secondary`, `text-primary`, `bg-ai-50`, `bg-warn-50`, …), never `bg-white` / `text-slate-*`, or the screen won't follow the theme. Settings, Knowledge, Routing, Billing, the Desk page and `ui/product/*` were converted.
- Inbox separation (committed `aebc0886`): tinted list and customer panel, white case area, tinted case header; customer / Tajeran / team / note entries each have their own colour.
- Not converted (still fixed colours): the unused `AppSidebar`, the logo mark, the old mission-board and builder screens, public and auth pages, and the chat widget on the store.

## 3c. Team and joining a workspace (2026-10-01; Team tab committed `906d1312`, the rest **not committed yet**)
- Settings → **Team** tab (`domains/workspace/TeamScreen.tsx`): invite by email + role (Agent / Manager / Admin) with the invite link shown for copying (create and resend return `invite_link`), member list with role change and Deactivate / Reactivate, Resend / Cancel for pending invites, and a plain "what each role can do" guide (mirrors `ROLE_PERMISSIONS` in `security/rbac.py`). The old Team box on the Workspace tab was removed.
- Owner's decisions: invite link (the teammate sets their own password), fixed roles, team panel before collaboration features.
- Joining: the invite link opens `/invite/accept?token=…` (`app/(auth)/invite/accept/page.tsx`). `GET /workspaces/invitations/preview` (public) names the workspace, email and role. Signed out → "Create an account" / "I already have an account" (token kept in `localStorage` `tajeran-invite-token`; `PendingInvite` in the app layout finishes the accept after login and email verification). Signed in with another email → "Log out and continue". Signed in with the right email → accepts and opens the Inbox.
- Which workspace opens: migration **`ui02`** adds `user.active_workspace_id` (applied to the dev database); accepting an invitation sets it, and `PrincipalResolver` opens it when no `X-Workspace-ID` header is sent and the user still belongs to it, else the personal workspace (test in `tests/tenancy/test_principal_context.py`). There is no workspace switcher yet, so a person who also owns a store cannot go back to it from the UI.
- Verified on 2026-10-01 against the dev backend: create → preview → resend (old link stops working) → cancel (link stops working), using made-up `example.com` addresses; the accept page's "wrong account" state at desktop and 375px. **Not verified:** the full join with a second real account (signing up needs email verification), and what a joined agent or manager actually sees. Known risk: some customer-service routes use `get_current_user` and key data by the user id, which equals the workspace id only for personal workspaces, so a joined teammate may see empty data on those routes until they are moved to the workspace principal.
- Signup does not prefill the invited email (the login page does); the signup page has the owner's changes in progress.

## 3d. Passwords (2026-10-01, **not committed yet**)
- Policy is now 8+ characters with at least one letter and one number (`validate_password_policy` in `backend/app/identity.py`; request limits in `api/auth.py`; tests in `tests/api/test_auth_identity_policy_http.py`). It was 12+ with lowercase, uppercase, number and symbol, while the sign-up and reset pages said "At least 8 characters", so valid-looking passwords were rejected.
- `ui/primitives/password-input.tsx` adds a show/hide eye; used on sign-up and reset-password (login already had one). Those two page files also carry the owner's uncommitted redesign, so committing them commits that work too.
- A Next.js page file may only export the page: an extra `export const` in `invite/accept/page.tsx` broke the typecheck and was removed.

## 4. Known gaps worth remembering
- Routing (`/app/routing`, **not committed yet**): the old lists and the sample-data button are gone; the sample agents, teams, queues and policies were deleted from the dev workspace with the owner's yes. The page is now "who gets what": a topic goes to one real team member, and "everything else" goes to a person, to whoever has the fewest open conversations, or stays unassigned. Rules are stored as `cs_routing_policies` rows with `meta.source = "assignment_rules"` (`services/assignment_rules.py`, `GET` / `PUT /studio/assignment-rules`) and applied in `_analyze_conversation` (`channels.py`) right after the topic is detected, only when the ticket has no assignee. Verified: with "Order status → Mehdi", an order-status chat was assigned and a general question stayed unassigned. The Inbox assignee menu now lists real workspace members (`CaseHeader.tsx`), not `cs_agents`. The older routing engine, teams, queues and agents tables are untouched and unused by this screen. Dev workspace has one rule saved: Order status → the owner.
- The job worker is now run with auto-reload in development (confirmed 2026-10-01: it restarted itself after a runtime code change).
- Reply language switching mid-conversation is fixed (the rule now quotes the latest customer message; verified live German → English on 2026-10-01; **not committed yet**).
- The job worker only loads code when it starts. Production deploys restart it, so this is a development-only chore; `watchfiles` is installed, so the worker could be started with auto-reload in development.
- The language rule wording was tightened after v23 went live (follow the latest customer message, not earlier ones: an English follow-up after a German message was answered in German). It is in `conversation_history.py`, **not committed**, and needs one more worker restart to take effect.
- Saving the Chat widget tab sends back the whole `meta` it loaded, so a tab left open for a long time can overwrite newer `unanswered_topics` (cached topics, dismissals). Worth moving those to their own table if this grows.
- Live → "Problems in the last 24 hours" still lists normal hand-overs as a problem row (now with the correct wording).
- "shipping information" was dismissed in the dev workspace while testing Task 9.
- `cs_conversation_insights.language` is rule-based and only knows en / es / fr / fa / ar (German is stored as `en`), so the Inbox can't flag a foreign-language chat by itself; the team clicks "Translate conversation". The fixed replies (hand-off, self-service, standby) are always English.
- The "Newest activity below" hint in the Case activity bar was replaced by the Translate control.
- Test conversation "Lena Test" (`187e9e7b-29e5-4328-8ca1-a3c0ef5aa0ef`) is a German chat created on 2026-10-01 for this check.
- "Orders after a support chat" shows 3 · $145 in the dev workspace. Those are test orders #1006–#1008, whose Shopify creation time is about 90 seconds after the first test chat (clock difference), so the match is a test-data artifact, not real influenced sales.
- "Track my order" reads the cached order when there is one; the cache is refreshed by Shopify webhooks, which don't reach localhost, so a status can be stale in development.
- The dev workspace now has a 60-minute reply target (24/7), set during testing on 2026-10-01; most old test conversations show "Reply target missed".
- The weekly schedule editor keeps one opening period per day; a day saved elsewhere with several periods would be reduced to the first on save. Holidays have no UI.
- Because the bot answers in seconds, "Answered within target" is close to 100%; the target matters mostly for conversations waiting for a person.
- The old chatbot page's controls for the attached workflow, minimum confidence and hand-off message are no longer in the UI (the values are kept). `chatbot/components/ChatbotHero.tsx`, `StorefrontPreviewPanel.tsx` and `ChatbotUi.tsx` are now unused.
- A self-service request shows in Live with the reason "No automation answered this message." A clearer reason would need its own marker.
- `public/widget-test.html` has no viewport meta tag, so the widget looks tiny at 375px on that page only.
- The bot answered a bare "1006" with the gift-wrapping article (conversation memory carried the earlier question).
- The dev workspace has all three self-service switches turned on (set during testing on 2026-10-01).
- The 7 tickets resolved before the `resolved_at` fix had their resolve time filled in from `updated_at` on 2026-10-01 (owner's yes), so their resolve times are approximate. One test ticket (`e40ba45e-36c7-40ac-aae0-354c848c06d3`, "John Duplicate Test") was resolved on 2026-10-01 to verify the fix.
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
