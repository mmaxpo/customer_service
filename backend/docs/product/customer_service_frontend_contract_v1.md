# Customer Service Product Frontend Contract V1

Sellable promise: **AI operations customer service for Shopify stores, supporting email and website chat.**

The backend is authoritative for tenancy, permissions, billing entitlements,
autopilot decisions, provider execution, and approval requirements. The frontend
must display these values and must never infer or grant them.

## Primary frontend areas

1. **Inbox** — conversations, customer/order context, suggested actions, reply
   composer, assignment, SLA and status.
2. **Automation activity** — one explainable feed for AI decisions, workflows,
   providers, approvals, failures/retries, verification, repair and learning.
3. **Autopilot settings** — per-intent mode, confidence, risk, channel and language
   guardrails.
4. **Knowledge** — URLs, files/PDFs, Shopify pages/policies, indexing freshness,
   citations, no-answer policy and evaluation questions.
5. **Shopify** — connection health, scopes and reauthorization, with mutations
   shown as approval workflows.
6. **Billing** — server-created Shopify checkout, verified subscription state and
   Shopify billing portal.

Every authenticated request should send `X-Workspace-ID`. Owner/admin can change
autopilot policy. Agents and viewers can read policy and activity; existing RBAC
still governs their other actions.

## Autopilot API

### Read policies

`GET /customer-service/autopilot/policies`

### Install conservative defaults

`POST /customer-service/autopilot/policies/seed-safe-defaults`

Recommended onboarding action. It creates a wildcard draft policy, allows only
high-confidence/low-risk tracking and product answers to auto-send, and requires
approval for refunds, cancellations and damaged-item operations.

### Create or replace an intent policy

`PUT /customer-service/autopilot/policies/{intent}`

```json
{
  "intent": "tracking_request",
  "mode": "auto_send_safe",
  "minimum_confidence": 0.92,
  "maximum_auto_risk": "low",
  "allowed_channels": ["email", "website_chat"],
  "allowed_languages": ["en", "fa"],
  "mutation_requires_approval": true,
  "is_enabled": true
}
```

Modes: `recommend_only`, `draft_reply`, `auto_send_safe`, `require_approval`,
and `never_automate`.

The backend always converts a protected mutation to `require_approval`, even if a
client submits `auto_send_safe`.

### Preview a policy decision

`POST /customer-service/autopilot/evaluate`

### Explain the current conversation decision

`POST /customer-service/conversations/{conversation_id}/autopilot/decision`

The response includes `decision`, `may_send`, `may_execute`,
`requires_approval`, `reason_codes`, the matched policy and classification
confidence. Use those fields directly for badges and controls.

## Unified automation activity

`GET /customer-service/conversations/{conversation_id}/automation-activity`

Optional repeated `category` query values and `limit` are supported. Categories:
`conversation`, `ai_decision`, `workflow_execution`, `provider_call`, `approval`,
`failure_retry`, `verification`, `repair`, and `learned_insight`.

Each event has a stable `id`, timestamp, title, status, workflow run reference,
entity reference and safe details. Provider credentials and token-like fields are
redacted by the backend. The UI can filter categories without understanding core
runtime event names.

## Intelligence contract

Conversation intelligence now returns structured `intent`, `sentiment`,
`urgency`, ISO `language`, calibrated `confidence`, `source` (`structured_model`,
`rule`, or `rule_fallback`), `model_version`, non-sensitive `fallback_reason`,
entities/order references, risks, opportunities and summary.

If the model is unavailable or rate-limited, deterministic multilingual rules
continue processing and autopilot uses the lower fallback confidence. The UI
should show a fallback badge but does not need to retry the model itself.

## Inbox behavior

For every new customer message the backend:

1. classifies the conversation;
2. generates suggestions and knowledge-backed drafts;
3. evaluates every action against workspace autopilot policy;
4. auto-sends only an allowed safe reply;
5. keeps low-confidence or failed delivery as a draft;
6. sends commerce mutations into the existing approval workflow;
7. records the decision and result in the activity feed.

The frontend should subscribe to existing realtime conversation events and
refresh the activity/suggestions panels after message, workflow or notification
events.

## Helpdesk operations

- `GET /customer-service/inbox?folder=inbox|snoozed|spam|all`
- `POST|DELETE /customer-service/conversations/{id}/snooze`
- `POST /customer-service/conversations/{id}/moderation`
- `POST /customer-service/conversations/bulk`
- `POST|GET /customer-service/conversations/{id}/drafts`
- `PUT|DELETE /customer-service/drafts/{id}` and `POST .../send`
- `GET|PUT /customer-service/reply-signatures...`
- `PATCH /customer-service/customers/{id}/custom-fields`
- `GET /customer-service/agents/productivity?days=30`

Snoozes are worker-backed and protect against stale wake jobs. Draft updates use
`expected_version`; treat HTTP 409 as an edit collision and reload the draft.
Outbound signatures are applied by the server, so the composer must not append
them. Spam/phishing conversations are quarantined before AI or workflows run.

## Business value

`GET /customer-service/analytics/business-value?days=30`

Render containment, first-contact resolution, approval wait, cost per resolved
conversation, AI acceptance/edit rate, revenue protected, refunds prevented,
CSAT by intent/workflow and provider failure rate from this response. Do not
recalculate these definitions in the frontend.

## Proactive playbooks

- `POST /customer-service/proactive/policies/seed-defaults`
- `GET /customer-service/proactive/policies`
- `PUT /customer-service/proactive/policies/{signal}`
- `POST /customer-service/proactive/evaluate`
- `GET /customer-service/proactive/incidents?status=open`
- `POST /customer-service/proactive/incidents/{id}/resolve`

Supported signals are repeated shipping delays, negative CSAT, VIP customers,
churn/chargeback risk, provider outage and repeated failed repairs. Policies set
threshold, lookback, cooldown and actions. Incidents are durable and may tag a
conversation, raise ticket priority and notify owners/admins. Seed defaults once
during merchant onboarding; this also starts recurring worker evaluation.

## Provider visibility

Show Shopify, email and website chat. WhatsApp, Instagram, Facebook and generic
omnichannel implementations remain in the backend but must stay hidden until
their production capability flag becomes available. They were not removed.
