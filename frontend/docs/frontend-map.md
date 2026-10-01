# Frontend Map — by responsibility

Next.js 15 (App Router) + React 19 + TypeScript, Tailwind 4, shadcn/Radix primitives, Zustand stores, `@xyflow/react` (+ dagre) for graphs, Motion for animation, Vitest + Playwright for tests. Source files per folder in brackets.

```
src/app (routes, thin) ──► src/domains/<product area> (screens, hooks, stores, api)
        │                          │
        │                          ├─► src/ui (shared look: layout, primitives, product widgets)
        │                          └─► src/platform (api client, events, realtime/SSE)
        └─ src/app/api/* (Next route handlers = proxy/BFF to the Python backend)
```

## 1. Routing — `src/app/` [75]
Route groups; pages should only mount a domain screen.
| Group | Pages |
|---|---|
| `(public)` | Landing `/`, `/contact` |
| `(auth)` | login, signup, forgot/reset-password, verify-email, `invite/accept` |
| `(app)/app/…` | The signed-in product: dashboard, inbox, live (+activity), routing, channels, chatbot, approvals, agents, knowledge, billing, operations, runs, `settings` (general, team, connections, chat-widget), `workflows` (builder, edit, history, mission-board, proposals, review, runs, templates) |
| `(workflows)` | Older standalone `runs/` and `workflow-builder/` |
| `(dev)` | `composer-test`, `dev-console` (developer-only) |

### BFF / proxy — `src/app/api/*`
Next route handlers between browser and Python backend: `auth/*` (login, logout, signup, refresh, me, password-reset, email-verification — sets/clears cookies), `contact`, `customer-service/[...path]`, `workspaces/[...path]`, `workflow-waits/[...path]`, `knowledge/*`, `workflows/*` (run, resume, runs, runtime, catalog), `catalog/tools`.

## 2. Domains (feature code) — `src/domains/` [~205]
| Domain | Responsibility |
|---|---|
| **`customer-service/`** [93] | The support-desk product UI |
| &nbsp;&nbsp;`inbox/` | Conversation list, case view (header, timeline, commerce panel, next step), reply composer, controller + hooks (`useInbox`, `useCase`, `useConversation`), services (inbox/conversation/reply), approvals and workflow-launcher features |
| &nbsp;&nbsp;`live/` | Live-now monitor, activity log, handoff notices |
| &nbsp;&nbsp;`automation/` | Workflow list, editor, graph, proposals, review queue, version history, unanswered topics |
| &nbsp;&nbsp;`routing/`, `channels/`, `chatbot/`, `approvals/`, `desk/` | Routing rules, channel connections, chat-widget settings, approvals screen, desk reports |
| &nbsp;&nbsp;`api/`, `model/` | Domain API calls and types |
| **`workflow/`** [103] | The generic workflow engine UI |
| &nbsp;&nbsp;`builder/` | Node-graph editor: canvas, nodes, edges, palette, inspector, toolbar, hooks, connection rules, import/export, runtime payload |
| &nbsp;&nbsp;`composer/` | Natural-language "describe your workflow" composer (blocks, hooks) |
| &nbsp;&nbsp;`mission-board/` | Mission-based planning view: compile mission, build run, knowledge graph, live view, Zustand store |
| &nbsp;&nbsp;`runner/` | Run viewer: SSE stream hook, hydration, run store, pause modal, runs list |
| **`workspace/`** [5] | Team screen (invite link, roles, members), settings tabs, theme switch, pending invite |
| **`knowledge/`** [4] | Knowledge console page + API |
| `auth/` | Empty |

## 3. Shared UI — `src/ui/` [25] and `src/components/` [7]
- `ui/layout/` — `AppShell`, `AppRail`, `AppHeader`, `AppSidebar`, `MobileNav`, `PageHeader`, `navigation.ts` (the nav tree)
- `ui/primitives/` — button, input, password-input, textarea, badge, card (shadcn-style)
- `ui/product/` — ProductPanel, StatCard, Tabs, Notice; `ui/overlay/`; `ui/brand/`
- `components/marketing/` — landing page pieces (Pricing, ProductTour, AuthShell, live-run demo, motion scenes)

## 4. Platform plumbing — `src/platform/` [21]
- `api/` — fetch client + typed calls (auth, customer-service, knowledge, tools, workflows, chat widget)
- `events/` — in-app EventBus (`useEvent`, `usePublish`)
- `realtime/` — `EventSourceClient`, `useWorkflowRunStream` (SSE)
- `capabilities/` — capability catalog model
- `backend.ts`, `utils.ts` — backend base URL, `cn` helper
- Empty placeholders: `auth/`, `config/`, `http/`, `runtime/`, `storage/`

## 5. Leftovers / structure debt
- **Duplicate API layers:** `platform/api/customer-service*.ts` vs `domains/customer-service/api/` (same file names), plus per-domain `api.ts` files.
- **Half-adopted FSD layers:** `entities/` [2] and `features/` [3] hold almost nothing; inbox code lives in `domains/…/inbox`.
- **Duplicate routes:** `(workflows)/runs` and `(app)/app/runs` and `app/workflows/runs`; `(workflows)/workflow-builder` vs `app/workflows/builder`.
- **Empty folders:** `src/lib`, `shared/{constants,date,types,utils}`, `ui/{feedback,forms,navigation,panels}`, `domains/auth`, `platform/{auth,config,http,runtime,storage}`, `components/dashboard`.
- `docs/` has earlier deep analyses (`tajeran_frontend_*`) worth cross-checking against this map.

## Backend ↔ frontend link
| Frontend | Backend |
|---|---|
| `domains/customer-service/*` | `app/domains/customer_service` via `api/products/customer_service/*` |
| `domains/workflow/*` + `runner` SSE | `app/runtime`, `app/tcos`, `app/workflow_operations` |
| `domains/workspace` | `app/tenancy` |
| `app/api/auth/*`, `(auth)` pages | `app/authentication`, `app/api/auth.py` |
| `domains/knowledge` | `app/services/knowledge_*`, `app/api/knowledge.py` |
