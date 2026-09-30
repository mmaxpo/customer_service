# V1 Feature Audit Tracker

One row per feature. Keep this file small and scannable — details go in
`.claude/features/<slug>.md`. Update the row the moment a feature file's
status changes; don't wait until the whole audit is done.

Status values: `not-started` · `in-progress` · `needs-work` · `done`

Suggested audit order: platform/foundation features first (they gate
everything else), then provider, then product, then the core AI/workflow
features that depend on all of them, then cross-layer glue last. This is a
suggestion, not a rule — pick whatever unblocks your team fastest.

| Feature | Layer | Status | Owner | File |
|---|---|---|---|---|
| Account & Workspace | platform | needs-work | — | features/account-workspace.md |
| Shopify Store Connection | provider | needs-work | — | features/shopify-store-connection.md |
| Shopify Commerce Context | provider | needs-work | — | features/shopify-commerce-context.md |
| Shopify Events | provider | needs-work | — | features/shopify-events.md |
| Shopify Actions | cross-layer | needs-work | — | features/shopify-actions.md |
| Inbox | product | needs-work | — | features/inbox.md |
| Customer Conversation | product | needs-work | — | features/customer-conversation.md |
| Customer Profile | product | needs-work | — | features/customer-profile.md |
| AI Customer-Service Agent | core | needs-work | — | features/ai-customer-service-agent.md |
| AI Knowledge | cross-layer | needs-work | — | features/ai-knowledge.md |
| AI → Human Handoff | cross-layer | needs-work | — | features/ai-human-handoff.md |
| AI Actions | cross-layer | needs-work | — | features/ai-actions.md |
| Human Approval | cross-layer | needs-work | — | features/human-approval.md |
| Basic Automation | product | needs-work | — | features/basic-automation.md |
| Basic Workflow | core | needs-work | — | features/basic-workflow.md |
| Website Chat + Channel Abstraction | product | needs-work | — | features/website-chat-channel.md |
| Email Channel | product | needs-work | — | features/email.md |
| Basic Ticketing | product | needs-work | — | features/basic-ticketing.md |
| Basic Routing | product | needs-work | — | features/basic-routing.md |
| Basic SLA | product | needs-work | — | features/basic-sla.md |
| Analytics | product | needs-work | — | features/analytics.md |
| AI Quality / Outcomes | core | needs-work | — | features/ai-quality-outcomes.md |
| Notifications | platform | needs-work | — | features/notifications.md |
| Audit & Security | platform | needs-work | — | features/audit-security.md |
| Billing & Usage | platform | needs-work | — | features/billing-usage.md |
<!--
This table was seeded from the V1 feature spec doc (25 features). Add a new
row here (and a matching file under features/) via /log-feature whenever a
26th feature shows up. Never delete a row — if a feature is dropped from
scope, set its status note accordingly instead of removing history.
-->
