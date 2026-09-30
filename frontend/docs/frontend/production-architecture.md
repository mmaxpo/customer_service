# Tajeran Frontend Production Architecture

## Current foundation

The frontend is organized around product features instead of generic page-only files.

Core product routes live under:

- `src/app/(product)/app/inbox`
- `src/app/(product)/app/workflows`
- `src/app/(product)/app/runs`
- `src/app/(product)/app/channels`
- `src/app/(product)/app/knowledge`
- `src/app/(product)/app/routing`
- `src/app/(product)/app/chatbot`

Feature implementation lives under:

- `src/features/customer-service`
- `src/features/workflows`
- `src/lib/api`
- `src/entities`

## Customer-service Inbox

The Inbox page is now a container/orchestration page. It should not grow back into a monolith.

Main file:

- `src/app/(product)/app/inbox/page.tsx`

Inbox components:

- `ConversationHeader.tsx`
- `ConversationMessages.tsx`
- `ReplyComposer.tsx`
- `RightSidebar.tsx`
- `CustomerPanel.tsx`
- `ShopifyOrderPanel.tsx`
- `TagsPanel.tsx`
- `AiWorkspacePanel.tsx`
- `WorkflowExecutionCard.tsx`
- `SlaStatusPanel.tsx`

Inbox hooks:

- `useInboxList`
- `useConversationWorkspace`
- `useConversationLoader`
- `useReplyActions`
- `useTicketActions`
- `useTagActions`
- `useSuggestedActions`
- `useConversationIntelligenceActions`
- `useCurrentUserId`

Inbox utilities:

- `loadConversationWorkspaceData`
- `loadShopifyOrderFromConversation`
- `orderRef`
- `workflowExecution`

Rule: new Inbox behavior should first go into a component, hook, or utility. Add to `page.tsx` only for orchestration.

## Workflow Composer

The merchant-friendly composer is now split into UI, hooks, and workflow construction utilities.

Main file:

- `src/features/workflows/composer/components/WorkflowComposer.tsx`

Core components:

- `BlockPalette.tsx`
- `BlockInspector.tsx`
- `ComposerNode.tsx`
- `MerchantFlowEdge.tsx`
- `ComposerPreviewPanel.tsx`

Hooks:

- `useComposerBlockActions`
- `useComposerSelectionActions`

Utilities:

- `backendTemplateFlow`
- `templateFlow`
- `starterFlow`
- `shopifyResultParsing`
- `compileToRuntimeWorkflow`
- `connectBlocks`
- `createBlock`

Rule: template construction and block creation logic should not live inside `WorkflowComposer.tsx`.

## API layer

Main customer-service API:

- `src/lib/api/customer-service.ts`

Chat widget API:

- `src/lib/api/customer-service-chat-widget.ts`

Shared entity types:

- `src/entities/customer-service`

Rule: avoid adding large type blocks to API files. Add shared product types to entities and keep API files focused on HTTP calls.

## Workflow UX strategy

There are two workflow experiences:

1. Merchant composer
   - simple business blocks
   - safe templates
   - Shopify/customer-service workflows

2. Advanced builder
   - full runtime DAG control
   - technical/debug mode
   - runtime node catalog and SSE run stream

The merchant composer should be the default product UX. The advanced builder should remain available for power users and internal debugging.

## Refactor checkpoint

Completed reductions:

- Inbox page reduced from about 1833 lines to about 632 lines.
- WorkflowComposer reduced from about 1467 lines to about 666 lines.
- customer-service API was partially split and chat-widget API extracted.

Verified:

- Frontend typecheck passes.
- Conversation delete tests pass.
- Chat tests pass.

## Next frontend development rules

Before adding new product features:

1. Check if the target file is already over 500 lines.
2. If yes, add a component/hook/util instead of expanding it.
3. Keep page files as route containers.
4. Keep domain logic under `features`.
5. Keep shared types under `entities`.
6. Keep HTTP calls under `lib/api`.
7. Run typecheck after every focused patch.

