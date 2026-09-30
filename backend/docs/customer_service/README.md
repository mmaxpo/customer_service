# Tajeran Customer Service Backend

This folder is the product contract for the customer-service backend before frontend implementation.

## Current Goal

Tajeran customer-service is an AI-native Shopify-first support OS.

The backend is now mature enough to power the first real frontend product:

- Omnichannel Inbox
- Conversation detail
- Ticket sidebar
- Customer 360
- AI reply
- Suggested actions
- Workflow visibility
- SLA/risk intelligence

## Backend API Categories

### 1. Core Entity APIs

Source-of-truth records.

- Customers
- Conversations
- Messages
- Tickets
- Tags
- Internal notes
- Macros
- Agents
- Teams
- Queues
- Routing policies

### 2. Intelligence APIs

Derived views that help agents decide what to do.

- Conversation context
- Conversation timeline
- Conversation intelligence snapshot
- Workspace recommendations
- Customer summary
- Customer activity
- Customer 360
- Customer risk score
- Customer risk leaderboard

### 3. Automation APIs

Workflow and automation visibility.

- Workflow templates
- Workflow executions
- Event subscriptions
- Shopify support workflows
- Chat automation settings
- Omnichannel inbound/outbound

### 4. Analytics APIs

Manager/dashboard reporting.

- Customer-service analytics
- Workload report
- Reply quality dashboard
- Reply quality trends
- Future dashboard aggregates
- Future agent productivity metrics

## Frontend Rule

Do not connect frontend randomly to every endpoint.

Each product screen should have a clear API contract.

Main first frontend screen:

`/app/inbox`

It should load in layers:

1. Inbox list
2. Selected conversation
3. Conversation intelligence
4. Customer/ticket sidebar
5. Workflow/activity panels lazy-loaded

## Backend Freeze Rule

Before moving to frontend, only add backend APIs that directly power:

- Inbox
- Dashboard
- Agent workspace
- Customer 360
- Workflow visibility

Avoid adding more CRUD unless frontend needs it.
