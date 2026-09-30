# Customer Service API Map

## Inbox

- `GET /customer-service/inbox/`
- `POST /customer-service/inbox/email/ingest`

## Conversations

- `POST /customer-service/conversations/`
- `GET /customer-service/conversations/`
- `GET /customer-service/conversations/{conversation_id}`
- `POST /customer-service/conversations/{conversation_id}/messages`
- `POST /customer-service/conversations/{conversation_id}/internal-notes`
- `POST /customer-service/conversations/{conversation_id}/triage`

## Conversation Intelligence

- `GET /customer-service/conversations/{conversation_id}/context`
- `GET /customer-service/conversations/{conversation_id}/timeline`
- `POST /customer-service/conversations/{conversation_id}/intelligence/analyze`
- `GET /customer-service/conversations/{conversation_id}/intelligence`
- `GET /customer-service/conversations/{conversation_id}/intelligence/snapshot`
- `GET /customer-service/conversations/{conversation_id}/workspace-recommendations`

## Customer 360

- `GET /customer-service/customers/`
- `POST /customer-service/customers/`
- `GET /customer-service/customers/{customer_id}/summary`
- `GET /customer-service/customers/{customer_id}/activity`
- `GET /customer-service/customers/{customer_id}/360`
- `GET /customer-service/customers/{customer_id}/risk`
- `GET /customer-service/customers/risk-leaderboard`

## Tickets

- `GET /customer-service/tickets/`
- `GET /customer-service/tickets/{ticket_id}`
- `PATCH /customer-service/tickets/{ticket_id}`
- `POST /customer-service/tickets/{ticket_id}/close`
- `POST /customer-service/tickets/{ticket_id}/reopen`
- `POST /customer-service/tickets/{ticket_id}/assign`
- `POST /customer-service/tickets/{ticket_id}/auto-assign`

## AI Reply + Agent Assist

- `POST /customer-service/conversations/{conversation_id}/ai-replies/compose`
- `POST /customer-service/conversations/{conversation_id}/ai-replies/regenerate`
- `POST /customer-service/conversations/{conversation_id}/summary/generate`
- `POST /customer-service/conversations/{conversation_id}/agent-assist/reply-suggestion`
- `GET /customer-service/conversations/{conversation_id}/agent-assist/suggestions`

## Suggested Actions

- `POST /customer-service/conversations/{conversation_id}/suggested-actions/generate`
- `GET /customer-service/conversations/{conversation_id}/suggested-actions`
- `POST /customer-service/suggested-actions/{action_id}/accept`
- `POST /customer-service/suggested-actions/{action_id}/reject`
- `POST /customer-service/suggested-actions/{action_id}/execute`

## SLA

- `POST /customer-service/sla/policies`
- `GET /customer-service/sla/policies`
- `GET /customer-service/sla/violations`
- `POST /customer-service/sla/check`

## Workflows

- `GET /customer-service/workflow-executions`
- `GET /customer-service/workflow-executions/{job_id}`
- `GET /customer-service/conversations/{conversation_id}/workflow-executions`
- `GET /customer-service/tickets/{ticket_id}/workflow-executions`
- `GET /customer-service/workflow-templates`
- `POST /customer-service/workflow-templates`
- `POST /customer-service/workflow-templates/seed-shopify`
- `POST /customer-service/workflow-templates/seed-website-chat`

## Shopify

- `POST /customer-service/shopify/connect`
- `GET /customer-service/shopify/orders/{order_ref}`
- `POST /customer-service/shopify/orders/{order_ref}/actions/{action}`
- `POST /customer-service/shopify/support-workflows/prepare`
- `POST /customer-service/shopify/install`
- `GET /customer-service/shopify/oauth/callback`

## Omnichannel

- `GET /customer-service/omnichannel/connections`
- `POST /customer-service/omnichannel/connections`
- `POST /customer-service/omnichannel/inbound`
- `POST /customer-service/omnichannel/outbound`
- `POST /customer-service/omnichannel/outbound/enqueue`
- `POST /customer-service/omnichannel/delivery-events`
- `GET /customer-service/omnichannel/providers/capabilities`

## Analytics

- `GET /customer-service/analytics/`
- `GET /customer-service/analytics/workload`
- `GET /customer-service/analytics/workload-report`
- `GET /customer-service/analytics/reply-quality`
- `GET /customer-service/analytics/reply-quality/dashboard`
- `GET /customer-service/analytics/reply-quality/insights`
- `GET /customer-service/analytics/reply-quality/trends`
