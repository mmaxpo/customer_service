# Feature: Basic Automation

## Spec
- **What it should do:** Merchant creates simple trigger → condition → action automations for repetitive support operations.
- **Layer:** product
- **Likely location (guess — verify, I don't have your repo):** domains/customer_service/automation (trigger → condition → action rules)
- **Key entities:** Automation, Trigger, Condition, Action, Automation Run
- **Core rules to check against:** Triggers: new conversation, new message, customer reply, Shopify event; actions: assign, tag, reply, escalate, start AI handling, create task, change status

## Acceptance criteria (from the v1 spec's "DONE" list)
- Triggers, conditions, actions all work
- Automations can be enabled/disabled; execution recorded
- Duplicate execution prevented; errors visible
- Tests cover representative automations

## Production success condition
> A merchant can automate repetitive support behavior reliably without manually operating each conversation.

## Audit Result
_Filled in by `/audit-feature basic-automation`. Re-run to refresh; each run overwrites this section only._

**Status:** needs-work

**What exists today:**
- Event subscriptions (triggers + conditions + actions): CustomerServiceEventSubscription model (models/workflows.py:35+), API endpoints for CRUD/enable/disable (automation.py:431-542)
- Workflow templates: CustomerServiceWorkflowTemplate model + API (create/list/clone/update/publish) — used to define automation logic as JSON
- Workflow executions: model + API (list/get/run/approve/reject), idempotency via execution tracking (repositories/workflow_executions.py)
- Trigger handlers: CustomerServiceWorkflowTriggerHandler.on_message_created() (workflows/trigger_handlers.py:13-49)
- Event publishing: PlatformEventPublisher for firing automations (used in tests/customer_service/workflows/test_customer_service_event_subscriptions.py:94)
- Pre-built templates: shopify_workflow_catalog.py (refund/cancel/shipping/damaged-item), chatbot_workflow_catalog.py (AI reply/order status)
- Enable/disable support: is_active flag in EventSubscription model and enable/disable endpoints
- Execution recording: workflow_executions model tracks status, user, timestamp
- Event types: customer_service.omnichannel.message.received, customer_service.omnichannel.message.sent, conversation.workflow_template.manual_run
- Filters: filters dict in EventSubscription schema for conditions
- Tests: extensive coverage including event_subscription_fanout, filter_matching, execution_idempotency, tracking

**Is it good enough?**
Partially. Strengths:
- Event → job → execution pipeline is solid
- Workflow execution tracking and idempotency work
- Tenant isolation enforced throughout
- Pre-built templates for Shopify and chat workflows

Gaps vs spec (basic trigger→condition→action):
- Event subscription API requires workflow_json (complex), no UI builder for simple trigger→condition→action
- Pre-built templates are AI/complex workflows (Shopify order lookup, LLM generation), not basic actions (assign, tag, reply, status change)
- No pre-built templates for: assign ticket, tag conversation, send simple reply, change status, escalate
- Error visibility: no dedicated API endpoint to fetch automation errors/failures for UI display
- Conditions only via filters dict — no predefined condition builders for "status = open", "priority = high", etc.
- No bulk/batch automation testing
- Message classification used for routing (trigger_handlers.py) but not exposed for merchant automations

**Gaps / risks:**
1. Missing basic action templates: spec requires assign/tag/reply/escalate/status — only AI workflows in catalog
2. No condition builder UI: filters are untyped dicts; no validation of condition syntax
3. Error visibility gap: execution errors not surfaced via API for UI error logs
4. Action nodes missing: no dedicated nodes for assign_ticket, tag_conversation, change_status, create_task, escalate_ticket
5. Shopify event trigger not wired: workflow executions track event_type but Shopify webhook integration incomplete for basic automations
6. No automation audit log: who triggered what automation, when, with what result
7. Template validation weak: no schema validation for workflow_json until runtime

## Task List
<!-- Concrete, agent-executable tasks: file path + exact change. -->
- [ ] Add basic action workflow templates: create basic_automation_workflow_catalog.py with pre-built templates for assign, tag, reply, status_change, escalate (no LLM/approval needed)
- [ ] Create action node types: add runtime/nodes/assign_ticket.py, tag_conversation.py, reply_conversation.py, change_ticket_status.py, escalate_ticket.py with execute() methods
- [ ] Add condition builder schema: create schemas/automation_conditions.py with predefined condition types (status, priority, channel, customer_segment) and validation
- [ ] Expose execution errors in API: add GET /customer-service/workflow-executions/{execution_id}/errors endpoint returning list of execution errors/failures
- [ ] Add automation audit log: add automation_executions table logging user, automation, result, timestamp; expose via GET /customer-service/automations/{automation_id}/executions
- [ ] Validate workflow JSON schema: in workflow_templates.py service, validate input/output schema before saving template
- [ ] Wire Shopify event triggers: add Shopify order event → workflow execution flow in shopify_provider_lifecycle.py
- [ ] Add tests for basic automation lifecycle: test_customer_service_basic_automation_assign.py covering trigger → assign → execution
- [ ] Add tests for error handling: test_customer_service_automation_error_visibility.py verifying error logs visible in API
- [ ] Add bulk automation test: test_customer_service_automation_batch_execution.py triggering automation on 100+ conversations 
