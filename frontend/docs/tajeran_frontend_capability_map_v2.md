# Tajeran Frontend Capability & Responsibility Map v2

Generated for the current Tajeran frontend refactor work from the uploaded `frontend(4).zip`, the previously produced frontend refactor audit, the backend capability map, and the latest local terminal evidence showing the Inbox route is already thin and imports `InboxController` from `@/domains/customer-service/inbox/controller`.

This document is not a UI wish list. It is the architecture map for turning the frontend into the same kind of controlled, durable, extensible system that the backend already is.

---

## 0. Executive summary

Tajeran's frontend should not be treated as a normal SaaS dashboard. The backend is an agentic business platform: runtime, workflows, agents, jobs, events, waits, replay, knowledge, ecommerce actions, omnichannel customer service, routing, SLA, and quality. The frontend has to become a product operating system that can expose those powers safely.

The correct frontend direction is:

```text
Next.js routes
  -> product/controller boundary
  -> workspace orchestration
  -> panels and widgets
  -> entity API/model layer
  -> shared UI and platform primitives
```

The uploaded `frontend(4).zip` still contains several large route-owned product pages. The user's local output, however, shows that the Inbox route has already evolved to:

```tsx
import { InboxController } from "@/domains/customer-service/inbox/controller";

export default function InboxPage() {
  return <InboxController />;
}
```

That is the right direction: route files should be routing only, and product behavior should live in product/domain/controller modules.

The new frontend architecture should evolve from scattered pages into:

```text
src/
  app/                    Next.js routing and API proxy only
  products/               buyer-facing product surfaces, e.g. customer-service, future sales/marketing/CRM
  platform/               runtime/workflow/jobs/events/knowledge operations shared by products
  entities/               typed domain models and API modules
  shared/                 UI primitives, formatting, hooks, config, api foundation
  components/layout/      global shell/navigation/layout only
```

During migration, the existing `src/domains/customer-service/...` is acceptable and should not be deleted. It should either become the customer-service product boundary or be gradually renamed to `src/products/customer-service` once stable.

---

## 1. Current source snapshot

### 1.1 Uploaded source file count

The uploaded source has `117` TypeScript/TSX files under `src`.

### 1.2 Largest files

| File | Lines |
|---|---:|
| src/app/(app)/app/inbox/page.tsx | 1833 |
| src/features/workflows/composer/components/WorkflowComposer.tsx | 1468 |
| src/lib/api/customer-service.ts | 812 |
| src/app/(app)/app/chatbot/page.tsx | 532 |
| src/app/(app)/app/routing/page.tsx | 417 |
| src/features/workflows/builder/components/WorkflowBuilder.tsx | 408 |
| src/app/(app)/app/workflows/page.tsx | 400 |
| src/app/(app)/app/channels/page.tsx | 346 |
| src/features/knowledge/components/KnowledgeConsole.tsx | 344 |
| src/features/workflows/composer/blocks/blockFactory.ts | 337 |
| src/app/(app)/app/knowledge/page.tsx | 324 |
| src/app/(app)/app/dashboard/page.tsx | 309 |
| src/features/workflows/composer/components/BlockPalette.tsx | 295 |
| src/features/workflows/runner/components/RunnerShell.tsx | 285 |
| src/features/workflows/builder/components/panels/NodeInspectorPanel.tsx | 284 |
| src/features/workflows/composer/blocks/blockDefinitions.ts | 257 |
| src/features/workflows/builder/utils/normalizeWorkflowNodes.ts | 224 |
| src/app/page.tsx | 217 |
| src/app/(public)/page.tsx | 217 |
| src/features/workflows/builder/components/panels/NodePalettePanel.tsx | 206 |
| src/features/workflows/builder/components/panels/RunOutputPanel.tsx | 204 |
| src/features/workflows/runner/components/RunsList.tsx | 190 |
| src/features/workflows/builder/hooks/useSavedWorkflows.ts | 188 |
| src/features/workflows/builder/utils/autoConfigureConnection.ts | 176 |
| src/features/workflows/builder/components/toolbar/WorkflowToolbar.tsx | 162 |
| src/features/workflows/builder/utils/normalizeRuntimeWorkflow.ts | 157 |
| src/features/workflows/builder/hooks/useWorkflowRunner.ts | 137 |
| src/features/workflows/runner/store/runStore.ts | 129 |
| src/features/workflows/composer/components/ComposerNode.tsx | 128 |
| src/features/workflows/composer/components/MerchantFlowEdge.tsx | 123 |
| src/app/(dev)/composer-test/page.tsx | 120 |
| src/features/workflows/composer/components/BlockInspector.tsx | 106 |
| src/features/workflows/builder/components/nodes/AgentNode.tsx | 106 |
| src/features/workflows/composer/types/composer.ts | 96 |
| src/features/workflows/builder/components/modals/HumanApprovalModal.tsx | 94 |

### 1.3 Current app routing tree from uploaded source

```text
(app)/
  app/
    AuthGate.tsx
    channels/
      page.tsx
    chatbot/
      page.tsx
    dashboard/
      page.tsx
    inbox/
      page-wrapper.tsx
      page.tsx
    knowledge/
      page.tsx
    layout.tsx
    routing/
      page.tsx
    runs/
      [runId]/
        page.tsx
      page.tsx
    settings/
      page.tsx
    workflows/
      builder/
        page.tsx
      page.tsx
(auth)/
  login/
    page.tsx
  signup/
    page.tsx
(dev)/
  composer-test/
    page.tsx
  dev-console/
    page.tsx
(public)/
  page.tsx
(workflows)/
  runs/
    [runId]/
      page.tsx
    page.tsx
  workflow-builder/
    page.tsx
api/
  auth/
    login/
      route.ts
    me/
      route.ts
  catalog/
    tools/
      route.ts
  customer-service/
    [...path]/
      route.ts
  knowledge/
    ask_agent/
      route.ts
    ask_agent_mcp/
      route.ts
    docs/
      [doc_id]/
        route.ts
      route.ts
    ingest/
      route.ts
    search/
      route.ts
  workflows/
    catalog/
      nodes/
        route.ts
    resume/
      route.ts
    run/
      route.ts
    runs/
      [runId]/
        state/
        stream/
      route.ts
    runtime/
      [workflowId]/
        route.ts
        run/
      route.ts
globals.css
layout.tsx
page.tsx
```

### 1.4 Current feature tree from uploaded source

```text
knowledge/
  components/
    KnowledgeConsole.tsx
workflows/
  builder/
    components/
      WorkflowBuilder.tsx
      edges/
        GradientEdge.tsx
      modals/
        HumanApprovalModal.tsx
        ImportWorkflowModal.tsx
        RuntimePayloadModal.tsx
      nodes/
        AgentNode.tsx
        EditableLabelNode.tsx
        TriggerNode.tsx
      panels/
        NodeInspectorPanel.tsx
        NodePalettePanel.tsx
        RunOutputPanel.tsx
      toolbar/
        WorkflowToolbar.tsx
    constants/
      initialWorkflow.ts
    hooks/
      useAgentTools.ts
      useCatalogView.ts
      useNodeCatalog.ts
      useSavedWorkflows.ts
      useWorkflowImportExport.ts
      useWorkflowNodes.ts
      useWorkflowRunner.ts
      useWorkflowSelection.ts
    store/
    types/
      catalog.ts
    utils/
      autoConfigureConnection.ts
      catalog.ts
      connectionRules.ts
      normalizeRuntimeWorkflow.ts
      normalizeWorkflowNodes.ts
      runtimePayload.ts
      toolConnections.ts
  composer/
    blocks/
      blockConnectionRules.ts
      blockDefinitions.ts
      blockFactory.ts
    components/
      BlockInspector.tsx
      BlockPalette.tsx
      ComposerNode.tsx
      MerchantFlowEdge.tsx
      WorkflowComposer.tsx
    index.ts
    types/
      composer.ts
    utils/
      compileToRuntimeWorkflow.ts
      connectBlocks.ts
      createBlock.ts
  runner/
    components/
      PauseModal.tsx
      RunnerShell.tsx
      RunsList.tsx
    hooks/
      useRunHydration.ts
      useRunStream.ts
    store/
      runStore.ts
    utils/
      sse.ts
  shared/
```

### 1.5 Current component/layout tree from uploaded source

```text
dashboard/
layout/
  AppContainer.tsx
  AppHeader.tsx
  AppShell.tsx
  AppSidebar.tsx
  EmptyState.tsx
  MobileNav.tsx
  PageHeader.tsx
  SectionCard.tsx
marketing/
ui/
  badge.tsx
  button.tsx
  card.tsx
  input.tsx
  textarea.tsx
```

### 1.6 Current API client tree

```text
api/
  auth.ts
  client.ts
  customer-service.ts
  index.ts
  knowledge.ts
  tools.ts
  workflows.ts
backend.ts
utils.ts
```

---

## 2. Product architecture thesis

Tajeran is not primarily a customer-service application. Customer service is the first application built on top of the core agentic platform.

The frontend should therefore have three clear layers:

```text
Layer 1: Platform capabilities
  workflow runtime, runs, replay, waits, events, jobs, agents, knowledge, webhooks, schedules

Layer 2: Product applications
  customer service first; later sales, marketing, CRM, ERP, support ops, security ops, etc.

Layer 3: Product workspaces
  inbox, chatbot, routing, channels, dashboard, knowledge, workflow templates, run debugger
```

A page should not own a product. A page should only mount a product controller.

Recommended route shape:

```tsx
import { CustomerServiceInboxController } from "@/products/customer-service/inbox/controller";

export default function Page() {
  return <CustomerServiceInboxController />;
}
```

The controller owns orchestration. Components own rendering. Entities own API/types. Shared owns visual primitives.

---

## 3. Dependency rules

These rules should become non-negotiable.

### 3.1 Allowed dependency direction

```text
app -> products -> platform -> entities -> shared
app -> platform -> entities -> shared
app -> shared
products -> entities -> shared
products -> platform -> entities -> shared
platform -> entities -> shared
entities -> shared
shared -> no app/product/platform/entity imports
```

### 3.2 Forbidden dependencies

```text
shared must not import products
shared must not import app routes
entities must not import products
entities must not import app routes
platform must not import products except through explicit extension/registration contracts
product components must not call fetch directly
route pages must not hold business state
route pages must not contain backend-specific business rules
```

### 3.3 Why this matters

Without dependency rules, every new product will copy customer-service patterns and the frontend will become harder to modify than the backend. With rules, each future product can be added without damaging Inbox, workflows, or global runtime UI.

---

## 4. Target folder responsibility map

```text
src/
  app/
    (app)/app/...              Next.js routes only
    api/...                    frontend API proxy routes only
    layout.tsx                 root HTML/layout only
    globals.css                design tokens/global styles

  products/
    customer-service/
      inbox/
      chatbot/
      routing/
      channels/
      dashboard/
      knowledge/
      workflows/
      customers/
      quality/
      analytics/

  platform/
    workflow-runtime/
    workflow-operations/
    jobs/
    events/
    knowledge/
    agents-runtime/
    webhooks/
    schedules/

  entities/
    customer-service/
      model/
      api/
    workflow/
      model/
      api/
    job/
      model/
      api/
    knowledge/
      model/
      api/
    auth/
      model/
      api/

  shared/
    api/
    config/
    hooks/
    lib/
    ui/
    state/
    telemetry/

  components/
    layout/
```

### 4.1 `src/app`

Responsibility: Next.js routing, route groups, server/client boundary, API proxies.

Should contain:

```text
page.tsx
layout.tsx
loading.tsx
error.tsx
route.ts
```

Should not contain:

```text
business state
complex useEffect data loading
inline product mutations
large JSX surfaces
formatting helpers
Shopify/Routing/SLA/Workflow logic
```

### 4.2 `src/products`

Responsibility: user-facing applications a merchant/admin/operator recognizes.

Examples:

```text
products/customer-service/inbox
products/customer-service/routing
products/customer-service/chatbot
products/customer-service/channels
products/customer-service/dashboard
```

Each product workspace should follow:

```text
controller.tsx
workspace.tsx
components/
hooks/
model/
utils/
index.ts
```

### 4.3 `src/platform`

Responsibility: frontend surfaces for generic backend platform capability.

Examples:

```text
platform/workflow-runtime
platform/jobs
platform/events
platform/knowledge
platform/agents-runtime
platform/webhooks
platform/schedules
```

A customer-service page may use workflow runtime widgets, but workflow runtime widgets should not depend on customer service.

### 4.4 `src/entities`

Responsibility: typed API modules, domain contracts, low-level data models, status helpers.

Examples:

```text
entities/customer-service/api/conversations.ts
entities/customer-service/api/tickets.ts
entities/customer-service/api/shopify.ts
entities/customer-service/model/types.ts
entities/customer-service/model/status.ts
```

### 4.5 `src/shared`

Responsibility: cross-product utilities and design system primitives.

Examples:

```text
shared/ui/Button.tsx
shared/ui/Card.tsx
shared/ui/Badge.tsx
shared/lib/date.ts
shared/lib/text.ts
shared/api/client.ts
shared/hooks/useAsyncAction.ts
```

---

## 5. Controller/workspace/component pattern

The local terminal output indicates Inbox now mounts an `InboxController`. That is a good pattern. It should become the standard for product workspaces.

### 5.1 Controller

A controller owns:

```text
initial data loading
mutation handlers
selection state
URL/query-param coordination
permissions and feature flags
error boundary decisions
composition of hooks
handing props to workspace
```

A controller should not own:

```text
large UI markup
low-level cards/buttons
formatting details
backend fetch implementation
```

### 5.2 Workspace

A workspace owns layout composition:

```text
left list
center content
right panel
top toolbar
empty/loading/error shells
```

### 5.3 Panels

Panels own a focused product responsibility:

```text
CustomerPanel
TicketPanel
OrderPanel
AIPanel
WorkflowPanel
SlaPanel
RoutingPanel
```

### 5.4 Widgets/cards

Widgets/cards should be reusable inside panels:

```text
SuggestedActionCard
WorkflowExecutionCard
WorkflowApprovalCard
MessageBubble
OrderSummaryCard
SlaStatusCard
```

---

## 6. Customer Service product map

Customer service is the first product. It should expose backend capability without becoming a blob.

### 6.1 Customer-service workspaces

```text
customer-service/inbox          live support workspace
customer-service/chatbot        website chat/widget automation
customer-service/routing        agents, teams, queues, policies
customer-service/channels       omnichannel + Shopify connections
customer-service/dashboard      product summary and readiness score
customer-service/customers      customer 360, activity, risk
customer-service/quality        reply quality, review, trends
customer-service/analytics      workload and operational metrics
customer-service/workflows      CS workflow templates and event subscriptions
```

### 6.2 Inbox responsibility

Inbox is the highest value customer-service surface because it combines:

```text
conversation list
conversation detail
message thread
reply composer
AI reply generation/regeneration
internal notes
tags
SLA state
ticket close/reopen/assign/auto-assign
Shopify order context/actions
workflow executions
workflow waits/approvals
suggested actions
conversation intelligence
customer context
```

Target shape:

```text
products/customer-service/inbox/
  controller.tsx
  workspace.tsx
  components/
    inbox-list/
      InboxList.tsx
      InboxListItem.tsx
    thread/
      ConversationThread.tsx
      MessageBubble.tsx
    reply/
      ReplyComposer.tsx
      InternalNoteComposer.tsx
    panels/
      CustomerPanel.tsx
      TicketPanel.tsx
      OrderPanel.tsx
      AIPanel.tsx
      WorkflowPanel.tsx
      SlaPanel.tsx
    cards/
      SuggestedActionCard.tsx
      WorkflowExecutionCard.tsx
      WorkflowApprovalCard.tsx
  hooks/
    useInboxList.ts
    useConversationWorkspace.ts
    useConversationActions.ts
    useAIReplyComposer.ts
    useShopifyOrderContext.ts
    useWorkflowApprovals.ts
  model/
    types.ts
    status.ts
  utils/
    formatters.ts
    orderRef.ts
    workflowExecution.ts
```

If the current local path is `src/domains/customer-service/inbox`, keep that path for now. Do not rename during active refactor. The architecture can later migrate `domains` to `products` with a clean move.

### 6.3 Chatbot responsibility

The chatbot page is not just a settings form. It is the control center for an autonomous website support agent.

It should own:

```text
widget settings
public key/install script
branding/position/preview
auto-answer threshold
human handoff behavior
workflow template attachment
website chat workflow seeding
```

Target shape:

```text
products/customer-service/chatbot/
  controller.tsx
  workspace.tsx
  components/
    ChatbotPreview.tsx
    ChatbotSettingsForm.tsx
    InstallScriptCard.tsx
    AutomationControls.tsx
    AttachedWorkflowCard.tsx
  hooks/
    useChatWidgetSettings.ts
    useChatbotTemplates.ts
  utils/
    installScript.ts
```

### 6.4 Routing responsibility

Routing is workforce automation, not only CRUD.

It should expose:

```text
agents
teams
queues
routing policies
skills
availability
capacity
best agent selection
auto assignment
seed demo workspace
```

Target shape:

```text
products/customer-service/routing/
  controller.tsx
  workspace.tsx
  components/
    AgentsPanel.tsx
    TeamsPanel.tsx
    QueuesPanel.tsx
    RoutingPoliciesPanel.tsx
    SeedRoutingWorkspaceButton.tsx
  hooks/
    useRoutingWorkspace.ts
    useSeedRoutingWorkspace.ts
```

### 6.5 Channels responsibility

Channels is the integration control center.

It should expose:

```text
channel list
channel connections
provider capabilities
Shopify OAuth/install
inbound simulation
outbound delivery job visibility
connection health
```

Target shape:

```text
products/customer-service/channels/
  controller.tsx
  workspace.tsx
  components/
    ChannelConnectionList.tsx
    ProviderCapabilityGrid.tsx
    ShopifyConnectPanel.tsx
    InboundTestPanel.tsx
    DeliveryStatusPanel.tsx
  hooks/
    useChannelsWorkspace.ts
```

### 6.6 Dashboard responsibility

The dashboard should not become the product center. Inbox is the product center. Dashboard should summarize readiness and operations.

It should show:

```text
inbox count
high priority count
knowledge docs
workflow runs
routing policies
setup readiness score
quick actions
recent activity
```

Target shape:

```text
products/customer-service/dashboard/
  controller.tsx
  workspace.tsx
  components/
    DashboardMetricCard.tsx
    ReadinessScoreCard.tsx
    RecentInboxPanel.tsx
    RecentWorkflowRunsPanel.tsx
    QuickActionsPanel.tsx
  hooks/
    useDashboardWorkspace.ts
```

---

## 7. Workflow/platform map

The workflow UI is the visual face of the backend runtime. It should be treated as platform capability, not only customer-service feature.

### 7.1 Existing workflow frontend from uploaded source

```text
features/workflows/builder
features/workflows/composer
features/workflows/runner
```

Builder is already relatively modular. Composer is too large and should be split. Runner is a good platform boundary candidate.

### 7.2 Workflow Builder

Responsibility:

```text
React Flow authoring
node catalog
node inspector
connection rules
runtime payload modal
human approval modal
run output panel
saved workflow definitions
```

Target:

```text
platform/workflow-builder/
  controller.tsx
  canvas/
  nodes/
  edges/
  panels/
  hooks/
  utils/
```

### 7.3 Workflow Composer

Responsibility:

```text
merchant-friendly workflow blocks
template loading
block graph state
compile to runtime workflow
run execution
Shopify result extraction
inspector/palette/canvas
```

Current biggest problem: `WorkflowComposer.tsx` is 1,468 lines.

Target:

```text
platform/workflow-composer/
  controller.tsx
  workspace.tsx
  components/
    WorkflowCanvas.tsx
    ComposerTopBar.tsx
    ComposerRunPanel.tsx
    ComposerTemplateLoader.tsx
    ComposerShopifyResultPanel.tsx
    BlockPalette.tsx
    BlockInspector.tsx
    ComposerNode.tsx
  hooks/
    useComposerGraph.ts
    useComposerTemplateLoader.ts
    useCompiledWorkflowRunner.ts
    useComposerLayout.ts
    useShopifyResultExtraction.ts
  utils/
    compileToRuntimeWorkflow.ts
    connectBlocks.ts
    createBlock.ts
    extractShopifyResult.ts
```

### 7.4 Workflow Runner

Responsibility:

```text
runs list
run hydration
SSE stream
pause/resume modal
run state store
```

Target:

```text
platform/workflow-runner/
  controller.tsx
  components/
    RunsList.tsx
    RunnerShell.tsx
    PauseModal.tsx
    RunTimeline.tsx
    RunStatePanel.tsx
  hooks/
    useRunHydration.ts
    useRunStream.ts
  store/
    runStore.ts
```

### 7.5 Missing workflow operations UI

The backend has workflow operations capabilities that are not yet surfaced enough:

```text
snapshots
replay
timeline
diff
versions
evaluations
metrics
quality gates
deployments
waits
```

These should become platform workspaces:

```text
platform/workflow-operations/snapshots
platform/workflow-operations/replay
platform/workflow-operations/timeline
platform/workflow-operations/diff
platform/workflow-operations/evaluations
platform/workflow-operations/deployments
platform/workflow-operations/waits
```

---

## 8. Entity/API layer map

The uploaded source currently has:

```text
src/lib/api/client.ts
src/lib/api/customer-service.ts
src/lib/api/workflows.ts
src/lib/api/knowledge.ts
src/lib/api/auth.ts
src/lib/api/tools.ts
```

The largest problem is `customer-service.ts` at 812 lines.

### 8.1 Target API split

```text
entities/customer-service/
  model/types.ts
  model/status.ts
  api/inbox.ts
  api/conversations.ts
  api/messages.ts
  api/tickets.ts
  api/tags.ts
  api/aiReplies.ts
  api/agentAssist.ts
  api/shopify.ts
  api/omnichannel.ts
  api/routing.ts
  api/sla.ts
  api/analytics.ts
  api/workflowTemplates.ts
  api/workflowExecutions.ts
  api/chatWidget.ts
  api/customers.ts
  api/quality.ts
  index.ts
```

### 8.2 Compatibility strategy

Do not break imports immediately. Keep:

```text
src/lib/api/customer-service.ts
```

as a compatibility facade:

```ts
export * from "@/entities/customer-service";
```

Only after all consumers migrate should the old file be deleted.

### 8.3 API ownership rule

Product controllers call entity API functions. Components do not.

Good:

```text
InboxController -> customerServiceConversationApi.getDetail()
```

Bad:

```text
MessageBubble -> customerServiceApi.addMessage()
```

---

## 9. Shared UI/design system map

The uploaded source has empty UI primitive files:

```text
src/components/ui/button.tsx
src/components/ui/card.tsx
src/components/ui/badge.tsx
src/components/ui/input.tsx
src/components/ui/textarea.tsx
```

These should be filled before extracting many product components.

### 9.1 Required primitives

```text
Button
Card
CardHeader
CardTitle
CardContent
Badge
Input
Textarea
Tabs
Panel
MetricCard
StatusBadge
LoadingState
ErrorBanner
EmptyState
Skeleton
```

### 9.2 Shared style rule

Repeated raw Tailwind should move downward into primitives. Product components should express intent, not every border/radius/spacing pattern.

Example:

```tsx
<StatusBadge tone="success">Published</StatusBadge>
```

instead of repeated:

```tsx
<span className="border-emerald-200 bg-emerald-50 text-emerald-700 ...">
```

### 9.3 Design token direction

Global tokens should cover:

```text
surface
surface-muted
border
text-primary
text-muted
success
warning
danger
info
focus ring
shadow levels
radius levels
```

---

## 10. State ownership map

### 10.1 Local component state

Use for:

```text
input draft values
open/closed panel state
selected tab inside a panel
hover/focus ephemeral state
```

### 10.2 Controller state

Use for:

```text
selected conversation
selected ticket/order/action
loading/error status
mutation in-flight status
workspace-level filters
query-param synchronization
```

### 10.3 Hook state

Use for reusable business orchestration:

```text
useInboxList
useConversationWorkspace
useAIReplyComposer
useWorkflowApprovals
useShopifyOrderContext
useRoutingWorkspace
useChannelsWorkspace
useWorkflowTemplates
```

### 10.4 Store state

Use only for truly shared runtime state:

```text
workflow run stream
multi-panel debugger state
auth session if needed
feature flags if needed
```

Do not put every form/list into a global store.

---

## 11. Server/client boundary

Current product pages are mostly client components because they need interactive state. That is acceptable.

Rule:

```text
Route page can be server or client, but it should only mount controller.
Controller can be client.
Workspace/components can be client when interactive.
API calls should happen through entity API modules.
```

For now, do not optimize server components prematurely. First fix ownership.

---

## 12. Navigation and information architecture

Current product navigation:

```text
Dashboard
Inbox
Channels
Chatbot
Knowledge
Routing
Workflows
Runs
Settings
```

Future navigation should separate:

```text
Customer Service
  Inbox
  Chatbot
  Channels
  Routing
  Customers
  Quality
  Analytics
  Workflows

Platform
  Workflow Builder
  Runs
  Jobs
  Events
  Webhooks
  Schedules
  Knowledge
  Evaluations

Settings
  Account
  Integrations
  Team
  Billing
```

This matters because merchants buy product outcomes, while builders/operators need platform capability.

---

## 13. Testing strategy

### 13.1 Current scripts

```text
npm run typecheck
tsc --noEmit
vitest run
playwright test
```

### 13.2 Required refactor safety gates

Every slice should pass:

```text
just type-check
```

Recommended later:

```text
unit tests for pure utils
component smoke tests for panels
controller tests with mocked APIs
Playwright happy path for Inbox
Playwright happy path for workflow run/resume
```

### 13.3 What to test first

```text
orderRef extraction
workflow execution wait matching
formatters
customer-service API facade exports
InboxController renders empty/loading states
ReplyComposer sends message callback
WorkflowApprovalCard approve/reject callbacks
```

---

## 14. Migration plan

The migration must be incremental. No more large blind moves.

### Phase 0 — Stabilize actual current local structure

The user's local output shows:

```text
src/app/(app)/app/inbox/page.tsx -> InboxController
src/domains/customer-service/inbox/components/workspace/ConversationWorkspace.tsx
src/domains/customer-service/inbox/components/reply/ReplyComposer.tsx
```

First inspect `src/domains/customer-service/inbox` before changing anything.

Commands:

```bash
find src/domains/customer-service/inbox -maxdepth 5 -type f | sort
find src/domains/customer-service/inbox -type f -name '*.tsx' -o -name '*.ts'
```

### Phase 1 — Document current local customer-service frontend

Create a local map:

```text
controller
workspace
components
hooks
model
utils
api imports
```

### Phase 2 — Standardize the Inbox architecture

Keep current path if it exists:

```text
src/domains/customer-service/inbox
```

Only later decide whether to rename to:

```text
src/products/customer-service/inbox
```

### Phase 3 — Extract other product pages to the same pattern

Order:

```text
chatbot
routing
channels
workflow templates
dashboard
knowledge
```

### Phase 4 — Split entity API layer

Split `customer-service.ts` after product modules are stable, or create entity API modules as wrappers first.

### Phase 5 — Platform surfaces

Add missing backend capability UIs:

```text
workflow snapshots/replay/timeline/diff
jobs/DLQ/replay
webhooks/endpoints/deliveries
schedules
platform events
agent runtime events/approvals/usage
workflow evaluations/quality gates/deployments
```

---

## 15. Immediate next commands for the real repo

Because the local frontend is not a Git repo, do not use `git diff` or `git apply` until it is initialized or inside the actual repository root.

Use direct inspection commands:

```bash
pwd
find src/domains/customer-service/inbox -maxdepth 5 -type f | sort
wc -l src/domains/customer-service/inbox/**/*.tsx src/domains/customer-service/inbox/**/*.ts 2>/dev/null
sed -n '1,220p' src/domains/customer-service/inbox/controller.tsx
sed -n '1,220p' src/domains/customer-service/inbox/components/workspace/ConversationWorkspace.tsx
```

Then run:

```bash
just type-check
```

The next implementation slice should be chosen only after reading those files.

---

## 16. Final architecture principle

Tajeran frontend should not mirror the backend folder names blindly. It should mirror the product truth:

```text
The backend gives powers.
The frontend gives operators control over those powers.
Products organize the user's work.
Platform modules organize reusable agentic/runtime capability.
Entities preserve typed contracts.
Shared UI preserves consistency.
Routes only mount controllers.
```

This is the frontend equivalent of the backend capability map.
