# Tajeran Frontend Deep Analysis

## Uploaded Archive Reviewed

Archive reviewed: `src.zip`

This archive contains the frontend `src/` tree only. It does not include `package.json`, lockfile, Tailwind config, Next config, tsconfig, or environment examples, so this analysis focuses on application structure, routes, product UX, API clients, and integration readiness.

---

## Quantitative Summary

| Area | Count |
|---|---:|
| TypeScript / TSX files | 116 |
| App files | 42 |
| Feature files | 50 |
| Shared component files | 13 |
| API/lib files | 9 |
| Test files | 2 |
| Total TS/TSX lines | about 13,062 |
| Largest file | `app/(app)/app/inbox/page.tsx` — about 1,681 lines |
| Second largest file | `features/workflows/composer/components/WorkflowComposer.tsx` — about 1,468 lines |

---

# 1. Frontend Mental Model

The frontend is a **Next.js App Router product UI** for Tajeran’s first product:

> AI-native omnichannel customer service for Shopify-first merchants, powered by workflow and agent orchestration.

It is already aligned with the backend capabilities:

- Inbox
- Channels
- Knowledge
- Workflows
- Workflow runs
- Routing
- Shopify support
- AI replies
- Suggested actions
- SLA/tickets/tags
- Omnichannel provider setup

This is not a generic admin panel. It is a product shell for a support operating system.

---

# 2. Route Structure

## Main Product Routes

Detected routes:

- `/app/dashboard`
- `/app/inbox`
- `/app/channels`
- `/app/knowledge`
- `/app/workflows`
- `/app/workflows/builder`
- `/app/runs`
- `/app/runs/[runId]`
- `/app/routing`
- `/app/settings`

## Auth Routes

- `/login`
- `/signup`

## Public Routes

- `/`
- `(public)/page.tsx` also exists and appears to duplicate the public landing page concept.

## Dev / Legacy Workflow Routes

- `/dev-console`
- `/composer-test`
- `/workflow-builder`
- `/runs`
- `/runs/[runId]`

Important note:

There are duplicate route groups for workflow builder/runs:

- Product route group: `/app/workflows/builder`, `/app/runs`
- Older/dev route group: `/workflow-builder`, `/runs`

Going forward, the product routes should become primary, and the older routes should either be removed, redirected, or clearly marked as dev-only.

---

# 3. Application Shell

The product shell is located under:

- `components/layout/AppShell.tsx`
- `components/layout/AppSidebar.tsx`
- `components/layout/AppHeader.tsx`
- `components/layout/MobileNav.tsx`
- `components/layout/PageHeader.tsx`
- `components/layout/SectionCard.tsx`
- `components/layout/AppContainer.tsx`

The sidebar navigation confirms the product structure:

- Dashboard
- Inbox
- Channels
- Knowledge
- Workflows
- Runs
- Routing
- Settings

Branding is already clear:

- `Tajeran.ai`
- `Support OS`
- Shopify inbox, AI replies, workflows, routing

The app route group is protected by:

- `app/(app)/app/AuthGate.tsx`

AuthGate calls `/api/auth/me`; failed auth redirects to `/login`.

---

# 4. API Layer

The frontend uses a strong pattern:

Browser/client components call local Next.js API routes under `/api/...`, and those routes proxy to the FastAPI backend.

## Core API client

- `lib/api/client.ts`

Provides:

- `apiFetch`
- `apiJson`
- `jsonBody`
- `apiSseUrl`
- `ApiError`

It enforces client API paths to start with `/api/`, which is good.

## Backend URL

- `lib/backend.ts`

Uses:

- `BACKEND_URL`
- `NEXT_PUBLIC_BACKEND_URL`
- fallback: `http://127.0.0.1:8000`

## Auth API

- `lib/api/auth.ts`
- `app/api/auth/login/route.ts`
- `app/api/auth/me/route.ts`

Login proxies to backend `/auth/login` and forwards `Set-Cookie`, which is important for session auth.

## Customer-Service API

- `lib/api/customer-service.ts`
- `app/api/customer-service/[...path]/route.ts`

The catch-all proxy maps:

`/api/customer-service/...` → `${BACKEND_URL}/customer-service/...`

This is the correct product API boundary.

## Workflow API

- `lib/api/workflows.ts`
- `app/api/workflows/...`

Covers:

- catalog nodes
- runtime workflow CRUD
- run workflow
- run saved workflow
- resume workflow
- list runs
- run state
- SSE stream URL

## Knowledge API

- `lib/api/knowledge.ts`
- `app/api/knowledge/...`

Covers:

- docs
- ingest
- delete doc
- search
- ask agent
- ask agent MCP

---

# 5. Customer-Service Frontend Coverage

The frontend already calls many backend customer-service capabilities.

## Inbox

Main file:

- `app/(app)/app/inbox/page.tsx`

This is the product center and is currently the biggest frontend file.

It covers:

- Inbox list
- Conversation detail
- Customer panel
- Messages
- Tickets
- Tags
- SLA violations
- AI reply compose/regenerate
- Conversation summary
- Conversation insights
- Suggested actions
- Shopify order lookup
- Shopify actions
- Workflow executions
- Internal notes
- Send message
- Add/remove tags
- Close/reopen ticket
- Assign/auto-assign ticket

Product conclusion:

The Inbox is correctly positioned as the core operating screen. This matches the earlier product decision: do not start from Dashboard; start from Inbox because the product center is conversations.

## Channels

Main file:

- `app/(app)/app/channels/page.tsx`

Covers:

- supported channels
- channel connections
- provider capabilities
- create manual connection
- Shopify OAuth install start
- provider catalog display

This matches backend omnichannel capabilities.

## Knowledge

Main files:

- `app/(app)/app/knowledge/page.tsx`
- `features/knowledge/components/KnowledgeConsole.tsx`

Covers:

- list docs
- ingest knowledge
- delete doc
- search docs
- ask agent
- ask agent MCP/debug paths

This supports AI reply grounding and workflow decision context.

## Routing

Main file:

- `app/(app)/app/routing/page.tsx`

Covers:

- agents
- teams
- queues
- routing policies
- create agent/team/queue/policy
- workspace setup for support routing

This aligns with backend routing policy/agent/team/queue tests.

## Dashboard

Main file:

- `app/(app)/app/dashboard/page.tsx`

Covers summary cards for:

- inbox count
- high-priority count
- knowledge docs
- workflow runs
- routing policies

Also has demo workspace creation:

- ingest demo knowledge
- create Shopify channel connection
- create routing objects
- seed workflow templates

Dashboard is useful as onboarding/demo, but it should not become the primary product surface.

---

# 6. Workflow Frontend Coverage

There are two workflow-building experiences.

## A. Technical Workflow Builder

Main files:

- `features/workflows/builder/components/WorkflowBuilder.tsx`
- `features/workflows/builder/...`

This is closer to a technical runtime editor.

It includes:

- React Flow nodes/edges
- node catalog
- tool catalog
- node inspector
- runtime payload builder
- workflow save/load
- workflow run
- human approval modal
- run output panel
- import/export
- runtime normalization

This builder maps more directly to backend workflow runtime internals.

## B. Merchant Workflow Composer

Main files:

- `features/workflows/composer/components/WorkflowComposer.tsx`
- `features/workflows/composer/blocks/blockDefinitions.ts`
- `features/workflows/composer/blocks/blockFactory.ts`
- `features/workflows/composer/utils/compileToRuntimeWorkflow.ts`

This is more product-friendly and business-facing.

Business blocks include:

- Customer Message
- Analyze Request
- Check Multiple Signals
- Manager Approval
- Make Decision
- Find Answer
- Tool Action
- Reply to Customer

These compile to backend runtime node types such as:

- `trigger.message`
- `agent.custom`
- `join.all`
- `human.approval`
- `router.rules`
- `kb.search`
- `llm.generate`
- `shopify.get_order`
- `shopify.order_action`
- `response`

Product conclusion:

This is a powerful direction. Long term, the merchant composer should become the main workflow creation UX, while the technical builder can remain internal/dev/admin.

---

# 7. Workflow Run UX

Main files:

- `features/workflows/runner/components/RunnerShell.tsx`
- `features/workflows/runner/components/RunsList.tsx`
- `features/workflows/runner/components/PauseModal.tsx`
- `features/workflows/runner/hooks/useRunHydration.ts`
- `features/workflows/runner/hooks/useRunStream.ts`
- `features/workflows/runner/store/runStore.ts`

State management uses:

- Zustand

Run UX supports:

- run hydration
- SSE event streaming
- node status updates
- pause interrupt handling
- resume through approval modal
- run details visualization

This aligns well with backend workflow timeline/SSE/pause-resume capabilities.

---

# 8. Design System / Styling

The frontend uses:

- Tailwind CSS v4 style `@import "tailwindcss";`
- `@theme` tokens inside `app/globals.css`
- custom Tajeran color tokens:
  - `tajeran`
  - `ai`
  - `shopify`
  - `warn`

The design direction is already coherent:

- dark Tajeran sidebar
- white card workspace
- rounded cards
- Shopify green accent
- AI purple accent
- workflow gradient styling

Important issue:

The files under `components/ui/` are empty:

- `badge.tsx`
- `button.tsx`
- `card.tsx`
- `input.tsx`
- `textarea.tsx`

This means the app currently uses mostly inline Tailwind classes instead of reusable UI primitives.

Future frontend polish should add real reusable UI primitives.

---

# 9. Testing Status

Detected frontend test files:

- `test/setup.ts`
- `test/smoke.test.tsx`

The test layer is currently minimal.

Unlike the backend, the frontend does not yet have strong tests around:

- auth redirect behavior
- API proxy behavior
- inbox loading/rendering
- composer compile behavior
- workflow run streaming
- routing/channel/knowledge flows
- form validation
- error states

This is an important gap before frontend becomes production-grade.

---

# 10. Current Strengths

## Strong Product Alignment

The frontend already understands the backend product:

- Inbox is central
- Shopify is first-class
- workflow automation is visible
- agent assist and suggested actions are present
- routing and channels are in product navigation
- knowledge is connected to AI/workflows

## Good API Boundary

The local Next.js API proxy pattern is good:

Frontend → `/api/...` → FastAPI backend

This avoids exposing backend URL directly to every browser call and makes cookies/session forwarding cleaner.

## Strong Workflow UX Direction

The presence of both technical builder and merchant composer is valuable.

The merchant composer is especially important because your target buyer should not need to understand runtime nodes.

## Real Product Pages Exist

This is not only a landing page. The app has real product surfaces:

- Inbox
- Channels
- Knowledge
- Workflows
- Runs
- Routing

---

# 11. Current Gaps / Risks

## 1. Inbox file is too large

`app/(app)/app/inbox/page.tsx` is about 1,681 lines.

This should eventually be split into:

- `InboxList`
- `ConversationHeader`
- `MessageTimeline`
- `ReplyComposer`
- `AIReplyPanel`
- `SuggestedActionsPanel`
- `ShopifyContextPanel`
- `TicketPanel`
- `TagsPanel`
- `SLAPanel`
- `WorkflowExecutionsPanel`
- hooks such as `useInbox`, `useConversationDetail`, `useAIReply`, `useSuggestedActions`

## 2. WorkflowComposer is too large

`WorkflowComposer.tsx` is about 1,468 lines.

This should eventually be split into:

- canvas
- toolbar
- block palette
- inspector
- save/load/run hooks
- import/export hooks
- execution/result panel

## 3. UI primitives are empty

The empty `components/ui/*` files should be implemented and then gradually used across product pages.

## 4. Duplicate route groups

There are duplicate workflow/run routes outside `/app`.

This can confuse future development.

Recommended:

- keep `/app/...` as production product routes
- move old workflow builder/dev console under `/dev/...`
- redirect old routes or delete them when no longer needed

## 5. Many `any` types

There are many `any` usages in workflow and dashboard code.

This is acceptable during rapid build, but future production frontend should use typed API contracts more deeply.

## 6. Console logs remain

Several workflow files have `console.log` debugging.

These should be removed or guarded behind dev mode before production.

## 7. No complete frontend config in archive

The upload only contains `src/`, so I could not verify:

- exact Next.js version
- React version
- Tailwind version
- TypeScript config
- path alias config
- ESLint config
- test runner config
- dependency versions

## 8. Signup page is only placeholder-level

`signup/page.tsx` is very small. Signup/onboarding is not yet a complete product flow.

## 9. Settings page is placeholder-level

`settings/page.tsx` is very small. Real merchant/product settings are not built yet.

---

# 12. Frontend vs Backend Alignment

## Already Aligned

| Backend Capability | Frontend Surface |
|---|---|
| Customer-service inbox | `/app/inbox` |
| Conversations/messages | Inbox detail |
| Tickets/tags/SLA | Inbox sidebar/panels |
| AI reply compose/regenerate | Inbox AI reply panel |
| Conversation intelligence | Inbox insights |
| Suggested actions | Inbox suggested actions |
| Shopify order/actions | Inbox Shopify context/actions |
| Omnichannel connections | `/app/channels` |
| Provider capabilities | Channels page |
| Knowledge docs/search/agent | `/app/knowledge` |
| Workflow templates | `/app/workflows` |
| Workflow runtime CRUD/run | Builder/composer |
| Workflow runs/SSE/resume | `/app/runs`, run detail |
| Routing agents/teams/queues/policies | `/app/routing` |

## Not Fully Surfaced Yet

Backend capabilities not yet deeply surfaced in frontend:

- event subscriptions UI
- webhook endpoint management
- quality review dashboards beyond basic hooks
- reply quality score analytics
- workflow metrics/snapshots/version comparison
- workflow deployments
- eval datasets/cases UI
- agent runtime budget/usage UI
- DLQ/jobs admin UI
- audit log browsing
- SLA policy management UI
- macros management UI
- team membership management depth
- full onboarding setup wizard
- merchant billing/plan/account settings

---

# 13. Updated Product Understanding

The frontend confirms the correct product narrative:

> Tajeran.ai is a Shopify-first AI customer-service operating system where the Inbox is the center, and every conversation can trigger AI analysis, Shopify context lookup, suggested actions, human approval, routing, and workflow automation.

The frontend should continue in this order:

1. Make Inbox excellent.
2. Make Shopify support context/action flow excellent.
3. Make suggested actions and AI reply flow excellent.
4. Make workflow templates usable from Inbox/Workflows.
5. Make Channels setup production-ready.
6. Make Routing usable for real support teams.
7. Add quality/analytics later after real usage data exists.

---

# 14. Recommended Next Development Priorities

## Priority 1: Refactor Inbox carefully

Do not rewrite it. Split it safely into components/hooks while preserving behavior.

## Priority 2: Turn merchant composer into product workflow builder

The composer is closer to what merchants understand.

Technical builder can remain available for internal/debug use.

## Priority 3: Add frontend tests around compile/API flows

Start with tests for:

- `compileToRuntimeWorkflow`
- `blockFactory`
- `customerServiceApi` path expectations
- AuthGate redirect behavior
- Inbox render with mocked API
- workflow run store event handling

## Priority 4: Implement UI primitives

Fill:

- Button
- Card
- Badge
- Input
- Textarea

Then migrate repeated classes gradually.

## Priority 5: Build onboarding

A first merchant onboarding should guide:

1. Connect Shopify
2. Add support channel
3. Add knowledge policy
4. Seed workflow templates
5. Open Inbox demo conversation
6. Send first AI-assisted reply

---

# 15. Final Conclusion

The frontend is already a serious first-product UI, not a toy app.

It is less mature than the backend test/migration layer, but it is directionally correct. The biggest frontend need is not architecture invention. The need is product hardening:

- component extraction
- real UI primitives
- stronger tests
- route cleanup
- onboarding flow
- production polish
- tighter typing
- better empty/error/loading states

The frontend and backend are aligned around the same product:

> AI-native omnichannel Shopify support powered by durable workflows and agents.