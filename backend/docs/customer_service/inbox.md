# Inbox Product Contract

Inbox is the center of Tajeran.

## Layout

### Left Panel: Conversation List

Purpose:

Show all active customer conversations.

Primary API:

`GET /customer-service/inbox/`

Data shown:

- customer name
- customer email
- channel
- subject
- latest message
- status
- ticket priority
- updated time

Frontend should load this first.

---

### Center Panel: Conversation Detail

Purpose:

Show the selected conversation and allow the agent to reply.

Primary APIs:

`GET /customer-service/conversations/{conversation_id}`

Optional/lazy APIs:

`GET /customer-service/conversations/{conversation_id}/timeline`

`GET /customer-service/conversations/{conversation_id}/context`

`GET /customer-service/conversations/{conversation_id}/intelligence/snapshot`

`GET /customer-service/conversations/{conversation_id}/workspace-recommendations`

Center panel should show:

- message timeline
- internal notes
- customer messages
- AI/agent replies
- reply composer
- AI reply button
- suggested actions

---

### Right Sidebar: Customer + Ticket

Purpose:

Give agent the customer and ticket context.

Primary APIs:

`GET /customer-service/customers/{customer_id}/summary`

`GET /customer-service/customers/{customer_id}/risk`

`GET /customer-service/tickets/{ticket_id}`

Optional/lazy APIs:

`GET /customer-service/customers/{customer_id}/activity`

`GET /customer-service/customers/{customer_id}/360`

Right sidebar should show:

- customer profile
- customer risk score
- total conversations
- total tickets
- open tickets
- channels
- ticket status
- priority
- assigned agent
- SLA risk
- tags

---

### AI Panel

Purpose:

Help agent respond faster and make better decisions.

Primary APIs:

`POST /customer-service/conversations/{conversation_id}/ai-replies/compose`

`POST /customer-service/conversations/{conversation_id}/ai-replies/regenerate`

`POST /customer-service/conversations/{conversation_id}/agent-assist/reply-suggestion`

`GET /customer-service/conversations/{conversation_id}/suggested-actions`

`POST /customer-service/conversations/{conversation_id}/suggested-actions/generate`

AI panel should show:

- suggested reply
- regenerate button
- confidence/quality
- suggested Shopify actions
- accept/reject/execute action

---

### Workflow Panel

Purpose:

Show automation visibility.

Primary API:

`GET /customer-service/conversations/{conversation_id}/workflow-executions`

Workflow panel should show:

- triggered workflows
- workflow status
- workflow result
- workflow error
- related event/subscription
- workflow run id if available

This panel should be lazy-loaded.
