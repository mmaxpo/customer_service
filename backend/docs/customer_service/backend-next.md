# Backend Next Work

This file tracks the last backend work before moving to frontend.

## Already Done

- Conversation Timeline API
- Conversation Context API
- SLA breach detection
- Customer Summary API
- Customer Activity API
- Customer 360 API
- Customer Risk API
- Customer Risk Leaderboard
- Conversation Intelligence Snapshot
- Workspace Recommendations

## Do Not Build Yet

### Giant Conversation Workspace API

Do not build this until frontend proves it is needed.

Reason:

It may become too heavy and confusing too early.

Current better approach:

Frontend loads:

1. `GET /inbox/`
2. `GET /conversations/{id}`
3. `GET /conversations/{id}/intelligence/snapshot`
4. `GET /conversations/{id}/workspace-recommendations`
5. Lazy-load timeline/context/workflow/customer360 as panels open.

## Recommended Next Backend APIs

### 1. Inbox Dashboard Aggregates

Endpoint:

`GET /customer-service/dashboard`

Purpose:

Power real dashboard cards.

Fields:

- open tickets
- pending tickets
- unassigned tickets
- SLA at risk
- high risk customers
- refund conversations
- workflow runs today

### 2. Customer Health Score

Endpoint:

`GET /customer-service/customers/{customer_id}/health`

Purpose:

Simpler merchant-friendly customer score.

Different from risk:

- risk = immediate support/churn danger
- health = long-term customer relationship

### 3. Agent Productivity Metrics

Endpoint:

`GET /customer-service/agents/productivity`

Purpose:

Manager dashboard.

Fields:

- assigned tickets
- closed tickets
- average first response
- average quality score
- reply count

### 4. Workflow Intelligence Panel

Endpoint:

`GET /customer-service/conversations/{conversation_id}/workflow-intelligence`

Purpose:

Show automation decisions inside Inbox.

Fields:

- workflows triggered
- workflow status
- decisions
- outputs
- errors
