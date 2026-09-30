# Tajeran Frontend Production Refactor Audit

Generated from inspection of `frontend(3).zip`.

## Executive summary

The frontend already has a useful product shell and a large amount of backend capability wired in. The biggest issue is not missing functionality; it is that several pages are acting as full feature modules. The main production refactor should move from **route-page-owned logic** to **feature-owned modules**.

The target architecture should be:

```text
src/app                         Next.js routing only
src/features/customer-service   inbox, dashboard, channels, routing, chatbot, customer 360
src/features/workflows          builder, composer, runner, templates
src/features/knowledge          knowledge console
src/entities                    shared typed domain models and small presentational cards
src/shared                      UI primitives, layout, formatting, hooks, api client, config
```

The highest priority is the Inbox route because it is 1,833 lines and currently contains data loading, state management, business logic, workflow approval logic, Shopify action handling, AI reply handling, tags, SLA, suggested actions, and the full UI layout in one component.

## Current structure observed

### App routes

```text
src/app/(product)/app/dashboard/page.tsx              309 lines
src/app/(product)/app/inbox/page.tsx                1833 lines
src/app/(product)/app/chatbot/page.tsx               532 lines
src/app/(product)/app/routing/page.tsx               417 lines
src/app/(product)/app/workflows/page.tsx             400 lines
src/app/(product)/app/channels/page.tsx              346 lines
src/app/(product)/app/knowledge/page.tsx             324 lines
src/app/(product)/app/runs/page.tsx                   20 lines
src/app/(product)/app/runs/[runId]/page.tsx           38 lines
src/app/(product)/app/workflows/builder/page.tsx      11 lines
src/app/(workflows)/workflow-builder/page.tsx     51 lines
src/app/(workflows)/runs/page.tsx                  7 lines
src/app/(workflows)/runs/[runId]/page.tsx         10 lines
```

The `/app` product routes are the current real product surface. The older `(workflows)` routes look like legacy/dev compatibility routes and should be reviewed for removal or redirect later.

### Shared layout

```text
src/components/layout/AppShell.tsx
src/components/layout/AppSidebar.tsx
src/components/layout/MobileNav.tsx
src/components/layout/AppHeader.tsx
src/components/layout/PageHeader.tsx
src/components/layout/SectionCard.tsx
src/components/layout/EmptyState.tsx
```

This is a good start. The app shell is already centralized.

### UI primitives

```text
src/components/ui/badge.tsx       0 lines
src/components/ui/button.tsx      0 lines
src/components/ui/card.tsx        0 lines
src/components/ui/input.tsx       0 lines
src/components/ui/textarea.tsx    0 lines
```

The UI primitives exist but are empty. This explains why pages repeat raw Tailwind patterns. Filling these primitives is a high-value refactor.

### API layer

```text
src/lib/api/client.ts              65 lines
src/lib/api/customer-service.ts   812 lines
src/lib/api/workflows.ts           86 lines
src/lib/api/knowledge.ts           41 lines
src/lib/api/auth.ts                14 lines
src/lib/api/tools.ts               17 lines
```

`customer-service.ts` is too large. It contains many domain types and all endpoint functions in one file. It should be split by backend responsibility.

## Backend capability to frontend responsibility map

The backend has powerful capabilities. The frontend should make those visible through clear product feature modules.

### 1. Customer Service OS / Inbox

Backend capabilities used:

```text
Inbox list
Conversation detail
Paginated messages
Tags
Internal notes
Suggested actions
AI reply compose/regenerate
Conversation intelligence
Conversation context
Timeline
SLA violations
Ticket close/reopen/assign/auto-assign
Workflow executions
Workflow waits/approvals
Shopify order context/actions
Omnichannel inbound/outbound
```

Current frontend file:

```text
src/app/(product)/app/inbox/page.tsx
```

Target feature structure:

```text
src/features/customer-service/inbox/
  pages/InboxPage.tsx
  components/InboxHeader.tsx
  components/InboxList.tsx
  components/InboxListItem.tsx
  components/ConversationThread.tsx
  components/MessageBubble.tsx
  components/ReplyComposer.tsx
  components/InternalNoteComposer.tsx
  components/CustomerPanel.tsx
  components/TicketPanel.tsx
  components/OrderPanel.tsx
  components/AIPanel.tsx
  components/SuggestedActionCard.tsx
  components/WorkflowExecutionCard.tsx
  components/WorkflowApprovalCard.tsx
  components/SlaStatusCard.tsx
  hooks/useInboxList.ts
  hooks/useConversationWorkspace.ts
  hooks/useConversationActions.ts
  hooks/useShopifyOrderContext.ts
  hooks/useWorkflowApprovals.ts
  hooks/useAIReplyComposer.ts
  utils/orderRef.ts
  utils/workflowExecution.ts
  utils/formatters.ts
  types.ts
```

Goal: `src/app/(product)/app/inbox/page.tsx` should become approximately:

```tsx
import { InboxPage } from '@/features/customer-service/inbox/pages/InboxPage';

export default InboxPage;
```

### 2. Agentic Workflow Builder / Composer / Runtime

Backend capabilities used:

```text
Workflow runtime
Workflow templates
Node catalog
Run execution
Run state
SSE stream
Wait/approval resume
Workflow replay/snapshots/timeline/diff/evaluations/metrics/quality
Customer-service workflow templates
Event subscription workflow dispatch
```

Current frontend files:

```text
src/features/workflows/builder/components/WorkflowBuilder.tsx      408 lines
src/features/workflows/composer/components/WorkflowComposer.tsx   1468 lines
src/features/workflows/runner/components/RunnerShell.tsx          285 lines
src/features/workflows/runner/components/RunsList.tsx             190 lines
src/app/(product)/app/workflows/page.tsx                              400 lines
```

Builder is already reasonably modular. Composer is the major oversized module.

Target feature structure:

```text
src/features/workflows/composer/
  pages/WorkflowComposerPage.tsx
  components/WorkflowCanvas.tsx
  components/ComposerTopBar.tsx
  components/ComposerRunPanel.tsx
  components/ComposerTemplateLoader.tsx
  components/ComposerShopifyResultPanel.tsx
  components/BlockPalette.tsx
  components/BlockInspector.tsx
  components/ComposerNode.tsx
  hooks/useComposerGraph.ts
  hooks/useComposerTemplateLoader.ts
  hooks/useCompiledWorkflowRunner.ts
  hooks/useComposerLayout.ts
  hooks/useShopifyResultExtraction.ts
  utils/compileToRuntimeWorkflow.ts
  utils/connectBlocks.ts
  utils/createBlock.ts
  utils/extractShopifyResult.ts
```

### 3. Workflow Templates Product Page

Backend capabilities used:

```text
List workflow templates
Seed Shopify workflow templates
Seed website chat templates
Clone templates
Publish/unpublish private templates
Open builder with template query params
```

Current frontend file:

```text
src/app/(product)/app/workflows/page.tsx 400 lines
```

Target structure:

```text
src/features/workflows/templates/
  pages/WorkflowTemplatesPage.tsx
  components/TemplateGrid.tsx
  components/TemplateCard.tsx
  components/TemplateStatusBadge.tsx
  hooks/useWorkflowTemplates.ts
```

### 4. Chatbot / Website Chat Automation

Backend capabilities used:

```text
Chat widget settings
Public key
Widget branding
Auto-answer controls
Confidence threshold
Human handoff
Workflow template attachment
Website chat workflow seed
```

Current frontend file:

```text
src/app/(product)/app/chatbot/page.tsx 532 lines
```

Target structure:

```text
src/features/customer-service/chatbot/
  pages/ChatbotPage.tsx
  components/ChatbotSettingsForm.tsx
  components/ChatbotPreview.tsx
  components/InstallScriptCard.tsx
  components/AutomationControls.tsx
  hooks/useChatWidgetSettings.ts
  hooks/useChatbotTemplates.ts
  utils/installScript.ts
```

### 5. Routing / Teams / Queues / Agents

Backend capabilities used:

```text
Agents
Teams
Queues
Routing policies
Agent capacity
Best agent selection
Auto assignment
```

Current frontend file:

```text
src/app/(product)/app/routing/page.tsx 417 lines
```

Target structure:

```text
src/features/customer-service/routing/
  pages/RoutingPage.tsx
  components/AgentsPanel.tsx
  components/TeamsPanel.tsx
  components/QueuesPanel.tsx
  components/RoutingPoliciesPanel.tsx
  components/SeedRoutingWorkspaceButton.tsx
  hooks/useRoutingWorkspace.ts
  hooks/useSeedRoutingWorkspace.ts
```

### 6. Channels / Omnichannel / Shopify

Backend capabilities used:

```text
Channel list
Omnichannel channel connections
Provider capabilities
Shopify OAuth install URL
Shopify connection creation
Inbound simulation
Outbound delivery jobs
```

Current frontend file:

```text
src/app/(product)/app/channels/page.tsx 346 lines
```

Target structure:

```text
src/features/customer-service/channels/
  pages/ChannelsPage.tsx
  components/ChannelConnectionList.tsx
  components/ProviderCapabilityGrid.tsx
  components/ShopifyConnectPanel.tsx
  components/InboundTestPanel.tsx
  hooks/useChannelsWorkspace.ts
```

### 7. Dashboard / Analytics

Backend capabilities used:

```text
Dashboard aggregates
Inbox summary
Recent workflow runs
Routing policies
Omnichannel simulation
```

Current frontend file:

```text
src/app/(product)/app/dashboard/page.tsx 309 lines
```

Target structure:

```text
src/features/customer-service/dashboard/
  pages/DashboardPage.tsx
  components/DashboardMetricCard.tsx
  components/RecentInboxPanel.tsx
  components/RecentWorkflowRunsPanel.tsx
  components/QuickActionsPanel.tsx
  hooks/useDashboardWorkspace.ts
```

### 8. Knowledge

Backend capabilities used:

```text
Knowledge ingestion
Document list/detail
Knowledge search
Ask agent
MCP ask agent
```

Current frontend files:

```text
src/app/(product)/app/knowledge/page.tsx
src/features/knowledge/components/KnowledgeConsole.tsx
```

Knowledge is already more feature-oriented than Inbox. It needs less urgent refactor.

## Major issues found

### Issue 1: Route pages contain feature logic

Examples:

```text
src/app/(product)/app/inbox/page.tsx
src/app/(product)/app/chatbot/page.tsx
src/app/(product)/app/routing/page.tsx
src/app/(product)/app/workflows/page.tsx
src/app/(product)/app/channels/page.tsx
src/app/(product)/app/dashboard/page.tsx
```

In production Next.js structure, route files should usually be thin. Feature behavior should live under `src/features`.

### Issue 2: Inbox page is too large

`InboxPage` currently owns:

```text
formatting helpers
order-ref extraction
workflow execution parsing
all state
all loading functions
all mutations
Shopify actions
AI actions
SLA actions
tag actions
internal note actions
message reply actions
conversation rendering
left list rendering
center thread rendering
right panel rendering
```

This should be split before adding more backend capability.

### Issue 3: customer-service API client is too large

`src/lib/api/customer-service.ts` should be split into modules:

```text
src/entities/customer-service/api/inbox.api.ts
src/entities/customer-service/api/conversations.api.ts
src/entities/customer-service/api/tickets.api.ts
src/entities/customer-service/api/ai.api.ts
src/entities/customer-service/api/shopify.api.ts
src/entities/customer-service/api/omnichannel.api.ts
src/entities/customer-service/api/routing.api.ts
src/entities/customer-service/api/workflow-templates.api.ts
src/entities/customer-service/api/chat-widget.api.ts
src/entities/customer-service/api/sla.api.ts
src/entities/customer-service/model/types.ts
src/entities/customer-service/index.ts
```

Keep a compatibility export during migration:

```text
src/lib/api/customer-service.ts -> re-export from new modules
```

### Issue 4: UI primitives are empty

The app has raw repeated Tailwind button/card/badge/input patterns. Filling these primitives will reduce repeated code and make future pages more consistent.

Immediate primitives:

```text
Button
Card
Badge
Input
Textarea
StatusBadge
MetricCard
LoadingState
ErrorBanner
EmptyState
Tabs
Panel
```

### Issue 5: duplicated public landing page

Both exist and are 217 lines:

```text
src/app/page.tsx
src/app/(public)/page.tsx
```

This likely duplicates the landing page. One should become canonical, the other should import/re-export or be removed.

### Issue 6: old workflow routes likely duplicate current app routes

Current product routes:

```text
/app/workflows/builder
/app/runs
/app/runs/[runId]
```

Older routes:

```text
/workflow-builder
/runs
/runs/[runId]
```

These should either be intentional dev compatibility routes or be turned into redirects to `/app/...`.

## Recommended refactor order

Do not refactor everything in one patch. Use small vertical slices with typecheck after each step.

### Phase 1 — Add shared foundation

1. Fill UI primitives.
2. Add shared formatters.
3. Add shared async state helper types.
4. Add shared domain status helpers.
5. Add customer-service API module folders while keeping compatibility exports.

### Phase 2 — Split Inbox safely

Start by extracting pure utilities from Inbox. This is low risk.

```text
utils/formatters.ts
utils/orderRef.ts
utils/workflowExecution.ts
```

Then extract hooks:

```text
useInboxList
useConversationWorkspace
useAIReplyComposer
useShopifyOrderContext
useWorkflowApprovals
```

Then extract components:

```text
InboxList
ConversationThread
ReplyComposer
RightPanel
SuggestedActionCard
WorkflowExecutionCard
```

Keep route behavior unchanged while moving code.

### Phase 3 — Split workflow composer

The composer is the second biggest file. Extract:

```text
template loading
graph state
layout
run execution
Shopify result extraction
```

### Phase 4 — Split app product pages

Refactor these pages into feature modules:

```text
chatbot
routing
channels
dashboard
workflow templates
```

### Phase 5 — Connect deeper backend power

After frontend structure is stable, add UI for backend capabilities currently underused:

```text
conversation context endpoint
timeline endpoint
workspace recommendations endpoint
customer 360 endpoint
risk leaderboard endpoint
workflow snapshots/timeline/diff/evaluations/metrics/quality
job queue/dead-letter visibility
schedule management
webhook endpoint management
```

## Production-grade target folder structure

```text
src/
  app/
    (app)/app/
      dashboard/page.tsx
      inbox/page.tsx
      channels/page.tsx
      chatbot/page.tsx
      routing/page.tsx
      workflows/page.tsx
      workflows/builder/page.tsx
      runs/page.tsx
      runs/[runId]/page.tsx
    api/
  shared/
    api/
      client.ts
      errors.ts
      query.ts
    config/
      env.ts
    ui/
      Button.tsx
      Card.tsx
      Badge.tsx
      Input.tsx
      Textarea.tsx
      Tabs.tsx
      MetricCard.tsx
      StatusBadge.tsx
      LoadingState.tsx
      ErrorBanner.tsx
    lib/
      cn.ts
      date.ts
      text.ts
  entities/
    customer-service/
      model/types.ts
      model/status.ts
      api/
        inbox.ts
        conversations.ts
        tickets.ts
        ai.ts
        shopify.ts
        omnichannel.ts
        routing.ts
        workflowTemplates.ts
        chatWidget.ts
      index.ts
    workflow/
      model/types.ts
      api/workflows.ts
      api/runs.ts
      api/waits.ts
      api/snapshots.ts
      index.ts
  features/
    customer-service/
      inbox/
      dashboard/
      channels/
      chatbot/
      routing/
      customers/
    workflows/
      templates/
      builder/
      composer/
      runner/
    knowledge/
  components/
    layout/
```

## First safe implementation slice

The first patch should not touch behavior. It should only move pure helpers and create shared primitives.

Suggested first slice:

```text
1. Create src/shared/lib/date.ts
2. Create src/features/customer-service/inbox/utils/orderRef.ts
3. Create src/features/customer-service/inbox/utils/workflowExecution.ts
4. Update InboxPage imports
5. Run typecheck
```

This reduces Inbox without changing UI or API behavior.

## Final recommendation

Refactor priority:

```text
1. Inbox page decomposition
2. customer-service API client split
3. shared UI primitives
4. workflow composer decomposition
5. chatbot/routing/channels/dashboard feature extraction
6. remove/redirect duplicate legacy workflow routes
7. add UI for deeper backend observability and workflow operations
```

The frontend is not weak. It is functionally rich, but it has outgrown page-level architecture. The next step is to convert it into a feature-owned frontend platform so it can expose the backend's full agentic workflow/customer-service power without becoming impossible to maintain.
