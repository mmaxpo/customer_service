# Frontend API Contract

## Canonical Customer Service API Client

File:

`src/lib/api/customer-service.ts`

Problem:

It is already too large.

Target split:

src/lib/api/customer-service/
├── index.ts
├── inbox.ts
├── conversations.ts
├── customers.ts
├── tickets.ts
├── intelligence.ts
├── recommendations.ts
├── workflows.ts
├── shopify.ts
├── chat.ts
└── types.ts

## First endpoints required for Inbox MVP

### Inbox list

`GET /api/customer-service/inbox/`

### Conversation detail

`GET /api/customer-service/conversations/{conversation_id}`

### Intelligence snapshot

`GET /api/customer-service/conversations/{conversation_id}/intelligence/snapshot`

### Workspace recommendations

`GET /api/customer-service/conversations/{conversation_id}/workspace-recommendations`

### Send reply

`POST /api/customer-service/conversations/{conversation_id}/messages`

### Internal note

`POST /api/customer-service/conversations/{conversation_id}/internal-notes`

### Tags

`GET /api/customer-service/conversations/{conversation_id}/tags/`
`POST /api/customer-service/conversations/{conversation_id}/tags/`
`DELETE /api/customer-service/conversations/{conversation_id}/tags/{name}`

## Lazy endpoints

Use only when panel opens:

- timeline
- context
- workflow executions
- customer activity
- customer 360
