# Inbox Refactor Plan

Current issue:

`src/app/(app)/app/inbox/page.tsx` is too large and mixes:
- data fetching
- state management
- filtering
- Shopify logic
- workflow logic
- SLA logic
- AI reply logic
- UI rendering

Target structure:

src/features/customer-service/inbox/
├── api.ts
├── types.ts
├── hooks/
│   ├── useInboxList.ts
│   ├── useConversationDetail.ts
│   ├── useConversationIntelligence.ts
│   ├── useWorkspaceRecommendations.ts
│   └── useInboxActions.ts
├── components/
│   ├── InboxShell.tsx
│   ├── ConversationList.tsx
│   ├── ConversationThread.tsx
│   ├── ReplyComposer.tsx
│   ├── CustomerSidebar.tsx
│   ├── TicketPanel.tsx
│   ├── IntelligencePanel.tsx
│   ├── RecommendationsPanel.tsx
│   └── WorkflowPanel.tsx
└── utils/
    ├── format.ts
    ├── orderRef.ts
    └── workflow.ts

Page target:

`src/app/(app)/app/inbox/page.tsx`

should become thin:

- render page shell
- call InboxShell
- no business logic
- no direct API calls
