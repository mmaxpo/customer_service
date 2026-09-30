# Tajeran.ai Backend Capability & Responsibility Map

Generated from the uploaded `app/` backend package. This document is written for two audiences:

1. **Backend developers** who need to extend the system safely.
2. **Frontend developers** who need a clear map of what backend capabilities exist and which APIs power each product surface.

The backend is not a simple CRUD API. It is an **agentic workflow + customer-service automation platform** with durable workflow execution, jobs, events, webhooks, schedules, AI agents, knowledge search, Shopify actions, omnichannel support, and a full customer-service product layer.

---

## 1. Top-level architecture

### Request/runtime composition

- `app/main.py` owns FastAPI app creation, lifespan startup, CORS, request middleware, tool container attachment, node catalog registration, checkpointer setup, and one central router include.
- `app/routers/main.py` is the application-level router registry. It includes auth, workflows, knowledge, agents runtime, customer service, jobs, schedules, webhooks, platform events, workflow operations, and email API.
- `app/domains/customer_service/main.py` is the domain-level router registry for the customer-service product.

### Router hierarchy

```text
app/main.py
  └── app/routers/main.py
        ├── app/routers/auth.py
        ├── app/routers/workflows.py + app/routers/workflows_route/*
        ├── app/agents_runtime via app/routers/agents_runtime.py
        ├── app/jobs/router.py
        ├── app/schedules/router.py
        ├── app/webhooks/router.py
        ├── app/platform/events/router.py
        ├── app/workflow_operations/* routers
        └── app/domains/customer_service/main.py
              └── app/domains/customer_service/routers/*
```

This is correct layering: top-level app composition does not need to know every customer-service route.

---

## 2. Major backend capabilities

| Capability | Main responsibility | Main folders |
|---|---|---|
| Agentic workflow runtime | Execute React Flow/DAG workflows with nodes, state, waits, approvals, replay, concurrency, persistence | `runtime/`, `routers/workflows_route/`, `workflow_operations/` |
| Agent runtime | Run autonomous/tool agents with state, events, approvals, tool registry, usage tracking | `agents_runtime/`, `routers/agents_runtime.py` |
| Durable jobs | Async durable execution for workflows, omnichannel outbound, retries, DLQ, recovery, metrics | `jobs/` |
| Platform events | Publish/record/dispatch platform events to workflow and customer-service handlers | `platform/events/` |
| Webhooks | Generic external webhook endpoints, signed payload verification, event normalization, workflow job enqueue | `webhooks/` |
| Schedules | Workflow schedules and scheduler tick mechanism | `schedules/` |
| Knowledge/RAG | Ingest documents, chunk, embed, search, answer through knowledge tools | `tools/knowledge/`, `services/knowledge_*`, `routers/knowledge_endpoints.py` |
| Customer-service product | Inbox, tickets, chat widget, omnichannel, Shopify, AI assist, routing, SLA, analytics, customer 360 | `domains/customer_service/` |
| Workflow operations | Snapshots, replay, timeline, metrics, diff, versions, evaluations, quality gates, deployments | `workflow_operations/` |
| Integrations governance | Circuit breaker, gateway, metrics and retry policy for external integrations | `integrations/`, `core/providers/` |

---

# 3. Agentic workflow platform

The workflow platform is the core engine under the product. It lets Tajeran define, run, pause, resume, replay, evaluate, and operate automations.

## 3.1 Workflow runtime responsibility

**Main folders:**

- `runtime/engine/`
- `runtime/catalog/`
- `runtime/nodes/`
- `runtime/state/`
- `runtime/waits/`
- `routers/workflows_route/`

### Runtime engine files/classes

- `runtime/engine/context.py`: `RuntimeContext` (__init__, app)
- `runtime/engine/executor.py`: `WorkflowExecutionError`
- `runtime/engine/persistence/memory.py`: `InMemoryRunStore` (__init__, create_run, update_run, load_run); `InMemoryEventSink` (__init__, emit)
- `runtime/engine/persistence/postgres.py`: `PostgresRunStore` (__init__, create_run, update_run, claim_run_for_resume, load_run, get_run, get_run_public, get_last_pause_interrupt); `PostgresEventSink` (__init__, emit)
- `runtime/engine/persistence/types.py`: `EventSink` (emit); `RunStore` (create_run, update_run, load_run)
- `runtime/engine/policy.py`: `ExecutionPolicy` (__init__, select_batch, can_continue)
- `runtime/engine/validator.py`: `ValidationError` (to_dict)
- `runtime/engine/workflow_repo.py`: `WorkflowRepo` (__init__, add, get_workflow)
- `runtime/engine/workflow_repo_postgres.py`: `PostgresWorkflowRepo` (__init__, create, get, list, update, delete)

### Runtime catalog files/classes

- `runtime/catalog/nodes/agent_custom.py`: `AgentCustomNode` (run)
- `runtime/catalog/nodes/agent_langgraph.py`: `AgentLangGraphNode` (run)
- `runtime/catalog/nodes/agent_mcp.py`: `AgentMCPNode` (run)
- `runtime/catalog/nodes/control_loop.py`: `ControlLoopNode` (run)
- `runtime/catalog/nodes/human_approval.py`: `HumanApprovalNode` (run)
- `runtime/catalog/nodes/join_all.py`: `JoinAllNode` (run)
- `runtime/catalog/nodes/kb_search.py`: `KBSearchNode` (run)
- `runtime/catalog/nodes/response.py`: `ResponseNode` (run, _resolve_answer, _format_answer)
- `runtime/catalog/nodes/router_llm.py`: `RouterLLMNode` (run)
- `runtime/catalog/nodes/router_rules.py`: `RouterRulesNode` (run)
- `runtime/catalog/nodes/set_variable.py`: `SetVariableNode` (run)
- `runtime/catalog/nodes/subworkflow_call.py`: `SubworkflowCallNode` (run)
- `runtime/catalog/nodes/trigger_message.py`: `TriggerMessageNode` (run)
- `runtime/catalog/nodes/wait_event.py`: `WaitEventNode` (run)
- `runtime/catalog/nodes/wait_time.py`: `WaitTimeNode` (run)
- `runtime/catalog/schemas.py`: `BaseNodeConfig`; `TriggerMessageConfig`; `KBSearchConfig`; `SetVariableConfig`; `AgentLangGraphConfig`; `AgentMCPConfig`; `Rule`; `RouterRulesConfig`; `RouterLLMConfig`; `JoinAllConfig`; `ResponseConfig`; `HumanApprovalConfig`; `SubworkflowCallConfig`; `LoopConfig`; `WaitTimeConfig`; `WaitEventConfig`
- `runtime/catalog/types.py`: `NodeCategory`; `NodeRunResult`; `RuntimeContext`

### Runtime node files/classes

- `runtime/nodes/base.py`: `BaseNode` (run)
- `runtime/nodes/customer_chat.py`: `CustomerChatReplyConfig`; `CustomerChatReplyNode` (run)
- `runtime/nodes/executor.py`: `NodeCtx` (__init__, __getattr__)
- `runtime/nodes/human_approval.py`: `HumanApprovalNode` (run)
- `runtime/nodes/knowledge_ingest.py`: `KnowledgeIngestConfig`; `KnowledgeIngestNode` (run)
- `runtime/nodes/knowledge_search.py`: `KnowledgeSearchConfig`; `KnowledgeSearchNode` (run)
- `runtime/nodes/llm_generate.py`: `LlmGenerateConfig`; `LlmGenerateNode` (run)
- `runtime/nodes/order_ref.py`: `ExtractOrderRefConfig`; `ExtractOrderRefNode` (run)
- `runtime/nodes/platform_job.py`: `PlatformJobEnqueueConfig`; `PlatformJobEnqueueNode` (run)
- `runtime/nodes/registry_support/registry_types.py`: `NodeRegistration`
- `runtime/nodes/shopify.py`: `ShopifyGetOrderConfig`; `ShopifyGetOrderNode` (run); `ShopifyOrderActionConfig`; `ShopifyOrderActionNode` (run)
- `runtime/nodes/web_fetch_extract.py`: `WebFetchExtractConfig` (_resolve_alias); `WebFetchExtractNode` (run)
- `runtime/nodes/web_search.py`: `WebSearchConfig` (_resolve_alias); `WebSearchNode` (run)

### What the workflow runtime can do

- Execute DAG workflows from React Flow-style JSON.
- Validate workflow shape before execution.
- Start workflow runs from trigger nodes.
- Run multiple ready nodes concurrently.
- Maintain run state and variable patches.
- Persist runs and events through memory or Postgres adapters.
- Pause workflows for human approval, time waits, and event waits.
- Resume paused workflows with payload injection.
- Replay from snapshots.
- Skip or block unsafe replay nodes.
- Execute domain/action nodes such as Shopify, customer chat reply, knowledge search, web search/fetch, platform job enqueue, order reference extraction, and LLM generation.

### Main workflow execution path

```text
API route / workflow job
  ↓
RuntimeContext
  ↓
execute_workflow_dag(...)
  ↓
validate_workflow
  ↓
build graph + find trigger
  ↓
initialize run lifecycle
  ↓
scheduler loop finds runnable nodes
  ↓
execute_node_batch
  ↓
apply successful results / pause / error / complete
  ↓
persist run state + events + snapshots
```

### Frontend usage

Frontend workflow builder should treat the backend as a durable workflow engine. Frontend responsibilities:

- Build React Flow JSON (`nodes`, `edges`).
- Call workflow validation before saving/running.
- Start workflow runs.
- Subscribe/read run events and state.
- Support pause/resume UX for approvals.
- Use snapshot/timeline/diff endpoints for debugging.

---

## 3.2 Workflow operations responsibility

**Folder:** `workflow_operations/`

These are operational capabilities around workflows after they exist and run.

- `workflow_operations/deployments/repository.py`: `WorkflowDeploymentRepository` (__init__, create, latest, list_for_workflow)
- `workflow_operations/deployments/schemas.py`: `WorkflowDeploymentCreate`; `WorkflowDeploymentRollbackRequest`; `WorkflowDeploymentRead`; `WorkflowDeploymentRollbackResult`
- `workflow_operations/deployments/service.py`: `WorkflowDeploymentService` (__init__, deploy, rollback, latest, list_for_workflow)
- `workflow_operations/diff/run_compare.py`: `WorkflowRunCompareService` (__init__, compare_runs, _final_snapshot, _compare_node_outputs, _node_outputs)
- `workflow_operations/diff/service.py`: `WorkflowStateDiffService` (compare_states, _dict_diff, _set_diff)
- `workflow_operations/diff/snapshot_compare.py`: `WorkflowSnapshotCompareService` (__init__, compare_snapshots)
- `workflow_operations/evaluations/dataset_repository.py`: `WorkflowEvalDatasetRepository` (__init__, create, get, list_for_user, delete)
- `workflow_operations/evaluations/dataset_schemas.py`: `WorkflowEvalCaseCreate`; `WorkflowEvalDatasetCreate`; `WorkflowEvalCaseRead`; `WorkflowEvalDatasetRead`
- `workflow_operations/evaluations/dataset_service.py`: `WorkflowEvalDatasetService` (__init__, create, get, list_for_user)
- `workflow_operations/evaluations/regression.py`: `WorkflowRegressionCheckRequest`; `WorkflowRegressionCaseDiff`; `WorkflowRegressionCheckResult`; `WorkflowRegressionDetector` (check)
- `workflow_operations/evaluations/schemas.py`: `WorkflowEvaluationCase`; `WorkflowEvaluationRequest`; `WorkflowEvaluationCaseResult`; `WorkflowEvaluationResult`; `WorkflowEvalCaseCreate`; `WorkflowEvalDatasetCreate`; `WorkflowEvalCaseRead`; `WorkflowEvalDatasetRead`
- `workflow_operations/evaluations/service.py`: `WorkflowEvaluationService` (__init__, run_evaluation, _run_case)
- `workflow_operations/metrics/repository.py`: `WorkflowMetricsRepository` (__init__, record_run_metric, list_for_user, summarize_version)
- `workflow_operations/metrics/service.py`: `WorkflowMetricsService` (__init__, record_from_workflow_result, summarize_version)
- `workflow_operations/quality/schemas.py`: `WorkflowQualityInput`; `WorkflowQualityScore`; `WorkflowDeploymentGateRequest`; `WorkflowDeploymentGateResult`
- `workflow_operations/quality/service.py`: `WorkflowQualityService` (score, deployment_gate, _score_metrics, _grade)
- `workflow_operations/snapshots/replay.py`: `WorkflowReplayService` (__init__, create_replay_job)
- `workflow_operations/snapshots/repository.py`: `WorkflowSnapshotRepository` (__init__, create, list_for_run, get)
- `workflow_operations/snapshots/schemas.py`: `WorkflowRunSnapshotRead`
- `workflow_operations/snapshots/service.py`: `WorkflowSnapshotService` (__init__, capture, list_for_run, get_or_404)
- `workflow_operations/timeline/service.py`: `WorkflowTimelineService` (__init__, get_timeline, _state_summary)
- `workflow_operations/versions/repository.py`: `WorkflowVersionRepository` (__init__, create_definition, get_definition, list_definitions, create_version, get_version, list_versions, publish_version)
- `workflow_operations/versions/schemas.py`: `WorkflowDefinitionCreate`; `WorkflowVersionCreate`; `WorkflowDefinitionOut`; `WorkflowVersionOut`
- `workflow_operations/versions/service.py`: `WorkflowVersionService` (__init__, create_definition, create_version, publish_version, rollback, get_active_version)
- `workflow_operations/waits/event_resolver.py`: `WorkflowWaitEventResolver` (__init__, resolve_for_event, _matches)
- `workflow_operations/waits/repository.py`: `WorkflowWaitRepository` (__init__, create, get_for_user, list_for_user, due_expired, claim_due_time_waits, resolve_waiting, save)
- `workflow_operations/waits/scheduler.py`: `WorkflowWaitScheduler` (__init__, expire_due, wake_due_time_waits)
- `workflow_operations/waits/schemas.py`: `WorkflowWaitCreate`; `WorkflowWaitResolve`; `WorkflowWaitRead`
- `workflow_operations/waits/service.py`: `WorkflowWaitService` (__init__, create, get_for_user, list_for_user, resolve, approve, reject, expire)

### Capabilities

- **Snapshots:** capture run state over time; replay a workflow from a snapshot.
- **Timeline:** show run events chronologically for debugging.
- **Diff:** compare snapshots or runs.
- **Versions:** define/version/publish workflow definitions.
- **Evaluations:** run workflow evaluation datasets and regression checks.
- **Metrics:** aggregate workflow performance and run summaries.
- **Quality:** score workflow quality and gate deployments.
- **Deployments:** manage deployment records and rollback.
- **Waits:** resolve waiting workflows from events/time.

### Frontend usage

These endpoints power workflow run detail, replay/debugger UI, version history UI, evaluation dashboards, deployment quality gates, and timeline/diff visualization.

---

## 3.3 Jobs responsibility

**Folder:** `jobs/`

- `jobs/dead_letter.py`: `DeadLetterRepository` (__init__, create_from_job, list_for_user, get, mark_replayed)
- `jobs/dead_letter_schemas.py`: `DeadLetterRead`
- `jobs/handlers.py`: `JobContext`; `JobHandlerRegistry` (__init__, register, get, job_types)
- `jobs/metrics.py`: `JobMetricsService` (__init__, queue_depth, counts_by_status, counts_by_type)
- `jobs/recovery.py`: `JobRecoveryService` (__init__, recover_abandoned)
- `jobs/replay.py`: `JobReplayService` (__init__, replay_dead_letter)
- `jobs/repository.py`: `JobRepository` (__init__, enqueue, get, list_for_user, claim_next_due, mark_succeeded, mark_failed, heartbeat)
- `jobs/retry.py`: `ExponentialBackoffRetry` (__init__, next_retry_at)
- `jobs/runner.py`: `JobWorkerRunner` (__init__, stop, run_forever)
- `jobs/schemas.py`: `JobCreate`; `JobRead`
- `jobs/service.py`: `JobService` (__init__, enqueue, get, list_for_user)
- `jobs/worker.py`: `JobWorker` (__init__, run_once, _fail_job, _call_handler, _heartbeat_until_done)

### Capabilities

- Enqueue durable jobs.
- Claim jobs with worker leases.
- Execute registered job handlers.
- Retry failed jobs with backoff.
- Move permanently failed jobs to dead-letter records.
- Recover stuck leased jobs.
- Replay dead-letter jobs.
- Publish job lifecycle platform events.
- Expose job list/detail/metrics endpoints.

### Current job-backed flows

- `workflow.run`
- `workflow.resume`
- `workflow.replay`
- webhook → workflow job
- event subscription → workflow job
- omnichannel outbound delivery
- Shopify action workflows

### What should become jobs later

Only move read/derived data into jobs when needed by scale or business need: dashboard metric snapshots, risk snapshots, scheduled recommendation refreshes, and merchant reports. Do **not** move everything to jobs prematurely. Live reads are fine when bounded and fast.

---

## 3.4 Platform events responsibility

**Folder:** `platform/events/`

- `platform/events/event_bus.py`: `PlatformEventBus` (__init__, publish)
- `platform/events/event_store.py`: `PlatformEventStore` (__init__, append, get, list_for_user, list_by_type)
- `platform/events/publisher.py`: `PlatformEventPublisher` (__init__, publish)
- `platform/events/registry.py`: `EventContext`; `EventHandlerRegistry` (__init__, subscribe, handlers_for, event_types)
- `platform/events/schemas.py`: `PlatformEventCreate`; `PlatformEventRead`

### Capabilities

- Store platform events.
- Publish events through an event bus.
- Invoke registered event handlers.
- Bridge platform events into workflow jobs.
- Resolve waits from events.
- Dispatch customer-service event subscriptions.

### Event-driven flow

```text
Domain action happens
  ↓
PlatformEventPublisher.publish(...)
  ↓
PlatformEventStore persists event
  ↓
EventHandlerRegistry finds handlers
  ↓
Handlers enqueue jobs / resolve waits / dispatch subscriptions
```

---

## 3.5 Webhooks responsibility

**Folder:** `webhooks/`

- `webhooks/providers/base.py`: `NormalizedWebhookEvent`; `WebhookProviderAdapter` (normalize)
- `webhooks/providers/generic.py`: `GenericWebhookAdapter` (normalize)
- `webhooks/providers/registry.py`: `WebhookProviderRegistry` (__init__, get)
- `webhooks/providers/shopify.py`: `ShopifyWebhookAdapter` (normalize)
- `webhooks/providers/stripe.py`: `StripeWebhookAdapter` (normalize)
- `webhooks/repository.py`: `WebhookRepository` (__init__, create_endpoint, get_endpoint, list_endpoints, create_delivery)
- `webhooks/schemas.py`: `WebhookEndpointCreate`; `WebhookEndpointRead`; `WebhookDeliveryRead`
- `webhooks/service.py`: `WebhookService` (__init__, create_endpoint, list_endpoints, receive, _verify_signature)

### Capabilities

- Create/list webhook endpoints.
- Receive external webhooks at `POST /webhooks/{endpoint_id}/{event_type}`.
- Verify signatures when a secret exists.
- Normalize provider payloads through provider adapters.
- Create webhook deliveries.
- Enqueue workflow jobs for configured endpoints.
- Supports generic, Shopify, and Stripe adapters.

### Frontend/admin usage

Frontend can expose webhook endpoint creation, endpoint list, secret copy flow, and delivery history/debugging.

---

## 3.6 Schedules responsibility

**Folder:** `schedules/`

- `schedules/repository.py`: `WorkflowScheduleRepository` (__init__, create, get_for_user, list_for_user, due, save)
- `schedules/scheduler.py`: `WorkflowScheduler` (__init__, tick)
- `schedules/schemas.py`: `WorkflowScheduleCreate`; `WorkflowScheduleRead`
- `schedules/service.py`: `WorkflowScheduleService` (__init__, create, list_for_user, get_for_user, pause, resume, _validate_create, _compute_initial_next_run)

### Capabilities

- Create workflow schedules.
- List schedules.
- Pause/resume schedules.
- Scheduler tick finds due schedules and enqueues workflow jobs.

---

# 4. Agents runtime

**Folder:** `agents_runtime/`

This is separate from workflow DAG runtime. It powers autonomous/tool-using agents with state, events, approvals, memory, usage tracking, and tool execution.

- `agents_runtime/config.py`: `AgentCustomConfig`
- `agents_runtime/events/recorder.py`: `EventRecorder` (__init__, emit, events, by_type, clear)
- `agents_runtime/events/store.py`: `AgentEventStore` (append, append_many, list_by_agent_run_id); `InMemoryAgentEventStore` (__init__, append, append_many, list_by_agent_run_id, clear); `PostgresAgentEventStore` (__init__, append, append_many, list_by_agent_run_id, list_by_run_id)
- `agents_runtime/events/stream.py`: `AgentEventStream` (__init__, publish, subscribe, subscriber_count)
- `agents_runtime/events/types.py`: `AgentEventType`; `AgentEvent`
- `agents_runtime/runner/agent_runner.py`: `AgentRunner` (__init__, _publish_and_persist_events, _persist_state, run, resume_after_approval)
- `agents_runtime/runner/context.py`: `AgentRuntimeContext`
- `agents_runtime/services.py`: `AgentRuntimeServices`
- `agents_runtime/state/machine.py`: `AgentStatus`; `InvalidAgentStateTransition`
- `agents_runtime/state/schemas.py`: `AgentError`; `PendingApproval`; `AgentState` (transition_to, mark_running, mark_paused, mark_completed, mark_failed, resume_from_pause)
- `agents_runtime/state/store.py`: `AgentStateStore` (save, load, delete); `InMemoryAgentStateStore` (__init__, save, load, delete, clear); `PostgresAgentStateStore` (__init__, save, load, delete)
- `agents_runtime/tools/executor.py`: `ToolExecutor` (__init__, execute)
- `agents_runtime/tools/registry.py`: `ToolRegistry` (__init__, register, get, list, selected, to_openai_tools)
- `agents_runtime/tools/schemas.py`: `ToolRiskLevel`; `AgentTool`
- `agents_runtime/usage/budget.py`: `UsageBudgetExceeded`; `UsageBudget` (check)
- `agents_runtime/usage/schemas.py`: `TokenUsage`; `AgentRunUsage` (add)
- `agents_runtime/usage/tracker.py`: `UsageTracker` (__init__, record_llm_response)

## Capabilities

- Run agent loops.
- Persist agent run state in memory/Postgres.
- Emit and stream agent events.
- Execute registered tools.
- Enforce tool risk/permission checks.
- Track token usage and budgets.
- Pause for approval and resume after approval.
- Support pure tool-agent, planner-executor, and LangGraph-style patterns.

## Frontend usage

Agent UX can start runs, read/stream event timelines, approve paused tool actions, and show state/usage.

---

# 5. Knowledge and tools layer

**Folders:** `tools/`, `tools/knowledge/`, `services/knowledge_ingest.py`, `services/knowledge_retrieval.py`, `services/knowledge_search.py`, `routers/knowledge_endpoints.py`.

## Responsibilities

- Common tool infrastructure: HTTP, cache, rate-limit, logging, typed tool responses.
- Knowledge ingest: chunk documents and store embeddings.
- Knowledge search: retrieve relevant context.
- Knowledge endpoints: search, ingest, delete docs, list docs, ask agent.
- Runtime/agent nodes use knowledge search as a tool.

---

# 6. Customer-service product domain

**Folder:** `domains/customer_service/`

This is the main business product layer. It is structured as:

```text
domains/customer_service/
  models/          SQLAlchemy ORM models grouped by responsibility
  schemas/         Pydantic API contracts
  repositories/    DB access/query logic
  services/        business logic/orchestration
  routers/         FastAPI endpoint boundary
  integrations/    provider adapters for Shopify/omnichannel
  workflows/       CS workflow classification/mapping/runtime bridge
  security/        RBAC/permission checks
```

## 6.1 Customer-service model responsibility

- `domains/customer_service/models/chat.py`: `CustomerChatWidgetSettings`; `CustomerChatSession`; `CustomerChatInboxLink`; `CustomerChatMessage`
- `domains/customer_service/models/core.py`: `Customer`; `Conversation`; `ConversationMessage`
- `domains/customer_service/models/enums.py`: `CustomerStatus`; `ConversationStatus`; `TicketStatus`; `TicketPriority`; `MessageSenderType`; `AgentAssistSuggestionStatus`; `SLATargetType`; `SLAViolationStatus`
- `domains/customer_service/models/omnichannel.py`: `CustomerServiceChannelConnection`; `CustomerServiceExternalConversationLink`; `CustomerServiceExternalMessageLink`; `CustomerServiceEventSubscription`
- `domains/customer_service/models/quality.py`: `AgentAssistSuggestion`; `AgentAssistSuggestionRevision`; `CustomerServiceConversationInsight`; `CustomerServiceSuggestedAction`; `CustomerServiceQualityReview`
- `domains/customer_service/models/routing.py`: `CustomerServiceRoutingPolicy`; `CustomerServiceAgent`; `CustomerServiceTeam`; `CustomerServiceQueue`; `CustomerServiceTeamMember`
- `domains/customer_service/models/shopify.py`: `CustomerServiceShopifyConnection`; `CustomerServiceShopifyOrderCache`; `CustomerServiceShippingTrackingCache`
- `domains/customer_service/models/sla.py`: `SLAPolicy`; `SLAViolation`
- `domains/customer_service/models/tickets.py`: `Ticket`; `TicketAssignment`; `ConversationTag`; `CustomerServiceAuditLog`; `CustomerServiceMacro`
- `domains/customer_service/models/workflows.py`: `CustomerServiceWorkflowTemplate`

### Model groups

- `models/core.py`: customers, conversations, conversation messages.
- `models/tickets.py`: tickets, assignments, conversation tags.
- `models/chat.py`: website chat widget settings, chat sessions/messages, inbox links.
- `models/sla.py`: SLA policies and violations.
- `models/shopify.py`: Shopify connection/cache/tracking cache.
- `models/omnichannel.py`: channel connections, external conversation/message links, event subscriptions.
- `models/routing.py`: routing policies, agents, teams, queues, members.
- `models/quality.py`: suggestions, quality reviews, reply quality, conversation intelligence.
- `models/workflows.py`: workflow templates and customer-service workflow-related records.
- `models/enums.py`: status/priority/sender enums.
- `models/models.py`: compatibility re-exports for older imports.

---

## 6.2 Customer-service repositories

Repositories own DB access. Services should use repositories instead of embedding queries in routers.

- `domains/customer_service/repositories/agent_assist.py`: `AgentAssistSuggestionRepository` (__init__, create, get, _system_message, list_revisions, next_revision_number, update_text, approve)
- `domains/customer_service/repositories/agents.py`: `CustomerServiceAgentRepository` (__init__, create, list_for_user, get, get_by_agent_user_id, list_by_agent_user_ids, update, delete)
- `domains/customer_service/repositories/analytics.py`: `AnalyticsRepository` (__init__, count_customers, count_conversations, count_tickets_by_status, count_tickets_by_priority, workload_by_assignee, open_sla_breaches, queue_workload)
- `domains/customer_service/repositories/audit_logs.py`: `AuditLogRepository` (__init__, create, list)
- `domains/customer_service/repositories/chat_repository.py`: `ChatRepository` (__init__, create_session, get_session, add_message, list_messages, get_widget_settings, get_or_create_widget_settings, get_widget_settings_by_public_key)
- `domains/customer_service/repositories/conversation_intelligence.py`: `ConversationInsightRepository` (__init__, get_conversation_with_messages, get_conversation_message_count, get_latest, upsert, list_for_conversation)
- `domains/customer_service/repositories/conversations.py`: `ConversationRepository` (__init__, get_by_id, create, list, get_detail, list_recent_context_messages, get_latest_workflow_message_meta, get_latest_customer_message)
- `domains/customer_service/repositories/customers.py`: `CustomerRepository` (__init__, create, list, get, summary)
- `domains/customer_service/repositories/event_subscriptions.py`: `CustomerServiceEventSubscriptionRepository` (__init__, create, list_for_user, list_active_for_event, get, update, delete, get_template)
- `domains/customer_service/repositories/inbox.py`: `InboxRepository` (__init__, list)
- `domains/customer_service/repositories/macros.py`: `MacroRepository` (__init__, create, list, get, update)
- `domains/customer_service/repositories/omnichannel.py`: `OmnichannelRepository` (__init__, create_connection, get_connection, list_connections, get_external_conversation, create_external_conversation, get_external_conversation_by_conversation_id, link_external_conversation)
- `domains/customer_service/repositories/quality_reviews.py`: `QualityReviewRepository` (__init__, create, list)
- `domains/customer_service/repositories/queues.py`: `CustomerServiceQueueRepository` (__init__, create, list_for_user, get, update, delete, team_belongs_to_user, list_by_ids)
- `domains/customer_service/repositories/reply_quality.py`: `ReplyQualityRepository` (__init__, create, list_for_conversation, aggregate_metrics, list_for_user)
- `domains/customer_service/repositories/routing_policies.py`: `CustomerServiceRoutingPolicyRepository` (__init__, create, list_for_user, get, update, delete, list_matching)
- `domains/customer_service/repositories/shipping.py`: `ShippingRepository` (__init__, find_cached_tracking, cache_tracking)
- `domains/customer_service/repositories/shopify.py`: `ShopifyRepository` (__init__, create_connection, get_active_connection, cache_order, find_cached_order)
- `domains/customer_service/repositories/sla.py`: `SLARepository` (__init__, create_policy, list_policies, get_active_policy_for_priority, create_violation_target, list_violations, list_open_due_targets, mark_breached)
- `domains/customer_service/repositories/suggested_actions.py`: `SuggestedActionRepository` (__init__, create, get_for_user, list_by_conversation, supersede_open_for_conversation, save)
- `domains/customer_service/repositories/tags.py`: `ConversationTagRepository` (__init__, add, list_for_conversation, remove)
- `domains/customer_service/repositories/teams.py`: `CustomerServiceTeamRepository` (__init__, create, list_for_user, get, update, delete, add_member, get_member)
- `domains/customer_service/repositories/ticket_assignment.py`: `TicketAssignmentRepository` (__init__, active_assignment, assign)
- `domains/customer_service/repositories/tickets.py`: `TicketRepository` (__init__, create, list, get, update, get_by_conversation, get_by_conversation_id)
- `domains/customer_service/repositories/workflow_executions.py`: `CustomerServiceWorkflowExecutionRepository` (__init__, list_for_user, get_for_user, _payload_event)
- `domains/customer_service/repositories/workflow_templates.py`: `WorkflowTemplateRepository` (__init__, create, list, get_system_by_name, get_for_user, update)

---

## 6.3 Customer-service services

Services own business logic, orchestration, side effects, and coordination between repositories/providers/jobs/events.

- `domains/customer_service/services/agent_assist.py`: `CustomerServiceAgentAssistService` (__init__, suggest_reply, list_conversation_suggestions, edit_suggestion, approve_suggestion, reject_suggestion, send_suggestion, list_revisions)
- `domains/customer_service/services/agent_capacity.py`: `AgentCapacityService` (__init__, current_workload, capacity_snapshot)
- `domains/customer_service/services/agents.py`: `CustomerServiceAgentService` (__init__, create, list_for_user, get, update, delete)
- `domains/customer_service/services/ai_context_policy.py`: `CustomerServiceAIContextPolicy` (from_env, trim_text)
- `domains/customer_service/services/ai_replies.py`: `AIReplyService` (__init__, compose_for_conversation, _latest_customer_message)
- `domains/customer_service/services/ai_reply_composer.py`: `CustomerServiceAIReplyComposer` (_compose_shopify_order_reply, compose, _reply_type)
- `domains/customer_service/services/ai_reply_regeneration.py`: `AIReplyRegenerationService` (__init__, regenerate)
- `domains/customer_service/services/analytics.py`: `AnalyticsService` (__init__, get_summary, workload, workload_report)
- `domains/customer_service/services/assignment.py`: `AssignmentService` (__init__, assign)
- `domains/customer_service/services/audit_logs.py`: `AuditLogService` (__init__, list_logs)
- `domains/customer_service/services/best_agent_selector.py`: `BestAgentSelector` (__init__, select_for_team, _matches_required_skills, _skill_score)
- `domains/customer_service/services/chat_service.py`: `CustomerChatService` (__init__, create_session, get_session, add_customer_message, add_ai_message, get_messages, get_or_create_widget_settings, get_widget_settings_by_public_key)
- `domains/customer_service/services/conversation_context.py`: `ConversationContextService` (__init__, get_context, _list_assignments, _list_sla_violations, _list_quality_reviews)
- `domains/customer_service/services/conversation_intelligence.py`: `ConversationIntelligenceService` (__init__, analyze, list_for_conversation, _detect_intent, _detect_sentiment, _detect_urgency, _detect_root_cause, _extract_entities)
- `domains/customer_service/services/conversation_intelligence_snapshot.py`: `ConversationIntelligenceSnapshotService` (__init__, get_snapshot, _conversation, _ticket, _tags, _sla_risk, _recommended_actions, _ticket_is_open)
- `domains/customer_service/services/conversation_summary.py`: `ConversationSummaryService` (__init__, generate)
- `domains/customer_service/services/customer_360.py`: `Customer360Service` (__init__, get_360, _get_customer, _recent_conversations, _recent_tickets, _tags_for_conversations)
- `domains/customer_service/services/customer_activity.py`: `CustomerActivityService` (__init__, _source_limit, list_activity, _get_customer, _list_conversations, _message_events, _ticket_events, _audit_events)
- `domains/customer_service/services/customer_risk.py`: `CustomerRiskService` (__init__, _leaderboard_candidate_limit, get_customer_risk, leaderboard, _customer, _conversation_ids, _tickets, _sla_breaches)
- `domains/customer_service/services/customers.py`: `CustomerService` (__init__, create_customer, list_customers, get_customer_summary)
- `domains/customer_service/services/dashboard.py`: `CustomerServiceDashboardService` (__init__, aggregates)
- `domains/customer_service/services/event_subscriptions.py`: `CustomerServiceEventSubscriptionService` (__init__, create, list_for_user, get, update, delete, enqueue_matching_workflows_for_event, _matches_filters)
- `domains/customer_service/services/inbox.py`: `InboxService` (__init__, get_inbox, list_conversations, create_conversation, get_conversation_detail, list_messages, add_message)
- `domains/customer_service/services/internal_notes.py`: `InternalNoteService` (__init__, add_note)
- `domains/customer_service/services/knowledge.py`: `CustomerServiceKnowledgeService` (__init__, search_context, _normalize_hit, _build_context)
- `domains/customer_service/services/macros.py`: `MacroService` (__init__, create, list, update, apply_to_conversation)
- `domains/customer_service/services/omnichannel.py`: `CustomerServiceOmnichannelService` (__init__, list_connections, create_connection, ingest_inbound_message, _delivery_status_rank, _max_delivery_status, apply_delivery_event, _get_or_create_customer)
- `domains/customer_service/services/quality_reviews.py`: `QualityReviewService` (__init__, review, list)
- `domains/customer_service/services/queues.py`: `CustomerServiceQueueService` (__init__, create, list_for_user, get, update, delete, _validate_team)
- `domains/customer_service/services/reply_quality.py`: `ReplyQualityService` (__init__, record_review, record_accept_without_edit, record_accept_with_edit, record_rejection, list_for_conversation, analytics, _default_score)
- `domains/customer_service/services/reply_quality_dashboard.py`: `ReplyQualityDashboardService` (__init__, dashboard)
- `domains/customer_service/services/reply_quality_insights.py`: `ReplyQualityInsightsService` (__init__, get_insights, _count, _rate, _average, _bucket, _source_value)
- `domains/customer_service/services/reply_quality_trends.py`: `ReplyQualityTrendsService` (__init__, get_trends, _window)
- `domains/customer_service/services/routing.py`: `CustomerServiceRoutingService` (__init__, auto_assign_ticket, decide_assignee)
- `domains/customer_service/services/routing_engine/engine.py`: `CustomerServiceRoutingEngine` (__init__, route_conversation)
- `domains/customer_service/services/routing_engine/matcher.py`: `RoutingPolicyMatcher` (matches)
- `domains/customer_service/services/routing_engine/selector.py`: `RoutingAssigneeSelector` (__init__, select)
- `domains/customer_service/services/routing_policies.py`: `CustomerServiceRoutingPolicyService` (__init__, create, list_for_user, get, update, delete, route_event, _event_matches_policy_filters)
- `domains/customer_service/services/shipping.py`: `ShippingService` (__init__, track, _normalize_tracking_number, _normalize_provider)
- `domains/customer_service/services/shopify.py`: `ShopifyService` (__init__, connect, get_order, prepare_support_workflow, perform_order_action, _find_shopify_action_by_idempotency_key, _record_shopify_action_idempotency_result, _order_ai_summary)
- `domains/customer_service/services/shopify_action_workflows.py`: `ShopifyActionWorkflowService` (__init__, start_action_workflow, _workflow_from_template)
- `domains/customer_service/services/shopify_context.py`: `ShopifyOrderReferenceExtractor` (extract); `ShopifyOrderContextResolver` (__init__, resolve)
- `domains/customer_service/services/shopify_order_context.py`: `ShopifyOrderContextBuilder` (build, _first_fulfillment_value)
- `domains/customer_service/services/shopify_support_orchestrator.py`: `ShopifySupportWorkflowOrchestrator` (__init__, handle, _decision, _next_action, _normalize_workflow_type)
- `domains/customer_service/services/shopify_workflow_decisions.py`: `ShopifySupportWorkflowDecisionService` (shipping_status, refund, cancel, change_address, damaged_item)
- `domains/customer_service/services/sla.py`: `SLAService` (__init__, create_policy, list_policies, list_violations, create_targets_for_ticket, check_breaches, resolve_first_response_targets, resolve_resolution_targets)
- `domains/customer_service/services/suggested_actions.py`: `SuggestedActionService` (__init__, generate, list, accept, reject, execute, _looks_like_tracking_request, _prepare_shopify_workflow_payload)
- `domains/customer_service/services/tags.py`: `ConversationTagService` (__init__, add_tag, list_tags, remove_tag)
- `domains/customer_service/services/teams.py`: `CustomerServiceTeamService` (__init__, create, list_for_user, get, get_detail, update, delete, add_member)
- `domains/customer_service/services/timeline.py`: `ConversationTimelineService` (__init__, _source_limit, get_timeline, _get_conversation, _get_ticket, _message_events, _tag_events, _assignment_events)
- `domains/customer_service/services/triage.py`: `AutoTriageService` (__init__, classify, classify_and_apply)
- `domains/customer_service/services/workflow_executions.py`: `CustomerServiceWorkflowExecutionService` (__init__, list, get, _normalize)
- `domains/customer_service/services/workflow_templates.py`: `WorkflowTemplateService` (__init__, create, list, seed_shopify_system_templates, seed_website_chat_system_templates, clone, update, publish)
- `domains/customer_service/services/workspace_recommendations.py`: `WorkspaceRecommendationsService` (__init__, get_recommendations, _build_recommendations, _automation_candidates, _overall_priority, _dedupe)

### Service responsibility groups

#### Inbox, conversations, customers, tickets

- `InboxService`: inbox list, conversation creation, detail, paginated messages, message add side effects.
- `CustomerService`: customer CRUD and customer summary.
- `CustomerActivityService`: bounded activity feed across conversations/messages/tickets/audits/workflows.
- `Customer360Service`: bundled customer view for support agents.
- `CustomerRiskService`: live customer risk score and bounded leaderboard.
- `ConversationContextService`: workspace bundle with bounded recent messages.
- `ConversationTimelineService`: bounded event timeline.

#### AI and agent assist

- `AIReplyService`: compose AI replies using bounded context, knowledge, intelligence, and optional Shopify context.
- `AIReplyRegenerationService`: regenerate replies using latest customer message.
- `CustomerServiceAIReplyComposer`: formats final reply and source summary.
- `CustomerServiceAgentAssistService`: creates, edits, approves, rejects, and sends agent-assist suggestions.
- `CustomerServiceAIContextPolicy`: single source of truth for message/context limits for model-facing features.
- `ConversationIntelligenceService`: rule-based intent/sentiment/urgency/entities/risks/opportunities.
- `ConversationIntelligenceSnapshotService`: combines intelligence, ticket, risk, SLA into an agent decision panel.
- `ConversationSummaryService`: bounded conversation summary.
- `SuggestedActionService`: generates next actions such as reply, assign, refund/cancel workflow suggestions.

#### Routing/SLA/workforce

- `SLAService`: policy creation, target creation, breach checks, first-response resolution.
- `CustomerServiceRoutingService`: auto-assignment orchestration.
- `CustomerServiceRoutingEngine`: match policies and select assignees.
- `RoutingPolicyMatcher`: checks policy conditions.
- `RoutingAssigneeSelector`: chooses teams/queues/agents.
- `AgentCapacityService`, `BestAgentSelector`: capacity snapshots and agent selection.
- `CustomerServiceAgentService`, `CustomerServiceTeamService`, `CustomerServiceQueueService`: workforce management.

#### Omnichannel/chat

- `CustomerChatService`: website chat sessions/messages/widget settings and inbox bridge.
- `CustomerServiceOmnichannelService`: inbound/outbound omnichannel, external links, delivery events, provider registry, job enqueue.
- `InboundEmailIngestService`: normalized inbound email into customer/conversation/ticket/message.

#### Shopify/ecommerce

- `ShopifyService`: connect shop, encrypted token storage, order lookup/cache, order action execution with idempotency, support workflow preparation.
- `ShopifyActionWorkflowService`: enqueue Shopify actions as workflows/jobs.
- `ShopifyOrderContextBuilder`: normalize Shopify order payload into support-friendly order context.
- `ShopifySupportWorkflowOrchestrator`: build safe action workflow plans.
- `ShopifySupportWorkflowDecisionService`: action decision/business logic.
- `ShippingService`: shipping/tracking lookup and cache.

#### Analytics/quality/workspace

- `AnalyticsService` / `AnalyticsRepository`: customer-service totals, ticket counts, workload reports.
- `CustomerServiceDashboardService`: dashboard aggregate counts.
- `ReplyQualityService`: record and analyze reply quality.
- `ReplyQualityDashboardService`, `ReplyQualityInsightsService`, `ReplyQualityTrendsService`: quality dashboards/insights/trends.
- `QualityReviewService`: quality review scoring and recommendations.
- `WorkspaceRecommendationsService`: agent next actions using intelligence snapshot + workflow execution state.

#### Workflow templates/executions/subscriptions

- `WorkflowTemplateService`: create/list/clone/update/publish/unpublish/seed templates.
- `CustomerServiceWorkflowExecutionService`: list workflow executions by user/conversation/ticket/job.
- `CustomerServiceEventSubscriptionService`: configure event subscriptions and enqueue matching workflow jobs.
- `CustomerServiceWorkflowRuntimeBridge`: bridge CS services into generic workflow runtime.
- `CustomerServiceWorkflowTriggerHandler`: triggers workflows from customer messages.

---

## 6.4 Customer-service workflows

- `domains/customer_service/workflows/message_classifier.py`: `CustomerServiceMessageClassifier` (classify)
- `domains/customer_service/workflows/runtime_bridge.py`: `CustomerServiceWorkflowRuntimeBridge` (__init__, run_reply_suggestion)
- `domains/customer_service/workflows/schemas.py`: `SupportIntent`; `MessageClassification`; `WorkflowAction`
- `domains/customer_service/workflows/trigger_handlers.py`: `CustomerServiceWorkflowTriggerHandler` (__init__, on_message_created)
- `domains/customer_service/workflows/workflow_mapper.py`: `CustomerServiceWorkflowMapper` (map_intent)

### Responsibilities

- Classify incoming messages into support intents.
- Map customer-service events/messages to workflow inputs.
- Build reply suggestion workflow definitions.
- Bridge customer-service workflow calls into generic runtime execution.
- Register omnichannel job handlers.

---

## 6.5 Customer-service router/API map

The customer-service API is mounted under `/customer-service`.

| Method | Path | Handler | Router file |
|---|---|---|---|
| GET | `/customer-service/inbox/` | `get_inbox` | `inbox` |
| POST | `/customer-service/inbox/email/ingest` | `ingest_email` | `inbox` |
| POST | `/customer-service/conversations/` | `create_conversation` | `conversations` |
| GET | `/customer-service/conversations/` | `list_conversations` | `conversations` |
| GET | `/customer-service/conversations/{conversation_id}/agent-assist/suggestions` | `list_conversation_agent_assist_suggestions` | `conversations` |
| GET | `/customer-service/conversations/{conversation_id}` | `get_conversation_detail` | `conversations` |
| POST | `/customer-service/conversations/{conversation_id}/triage` | `triage_conversation` | `conversations` |
| POST | `/customer-service/conversations/{conversation_id}/internal-notes` | `add_internal_note` | `conversations` |
| GET | `/customer-service/conversations/{conversation_id}/messages` | `list_conversation_messages` | `conversations` |
| POST | `/customer-service/conversations/{conversation_id}/messages` | `add_message` | `conversations` |
| POST | `/customer-service/conversations/{conversation_id}/agent-assist/reply-suggestion` | `reply_suggestion` | `conversations` |
| PATCH | `/customer-service/conversations/agent-assist/suggestions/{suggestion_id}` | `edit_agent_assist_suggestion` | `conversations` |
| POST | `/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/approve` | `approve_agent_assist_suggestion` | `conversations` |
| POST | `/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/reject` | `reject_agent_assist_suggestion` | `conversations` |
| POST | `/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/send` | `send_agent_assist_suggestion` | `conversations` |
| GET | `/customer-service/conversations/agent-assist/suggestions/{suggestion_id}/revisions` | `list_agent_assist_suggestion_revisions` | `conversations` |
| POST | `/customer-service/customers/` | `create_customer` | `customers` |
| GET | `/customer-service/customers/` | `list_customers` | `customers` |
| GET | `/customer-service/customers/{customer_id}/summary` | `get_customer_summary` | `customers` |
| GET | `/customer-service/customers/{customer_id}/activity` | `get_customer_activity` | `customers` |
| GET | `/customer-service/customers/{customer_id}/360` | `get_customer_360` | `customers` |
| GET | `/customer-service/customers/{customer_id}/risk` | `get_customer_risk` | `customers` |
| GET | `/customer-service/customers/risk-leaderboard` | `customer_risk_leaderboard` | `customers` |
| GET | `/customer-service/channels/` | `get_channels` | `channels` |
| GET | `/customer-service/workflows/` | `get_workflows` | `workflows` |
| GET | `/customer-service/analytics/` | `get_analytics` | `analytics` |
| GET | `/customer-service/analytics/workload` | `workload_report` | `analytics` |
| GET | `/customer-service/analytics/workload-report` | `workload_visibility_report` | `analytics` |
| GET | `/customer-service/dashboard` | `get_dashboard_aggregates` | `dashboard` |
| GET | `/customer-service/tickets/` | `list_tickets` | `tickets` |
| GET | `/customer-service/tickets/{ticket_id}` | `get_ticket` | `tickets` |
| PATCH | `/customer-service/tickets/{ticket_id}` | `update_ticket` | `tickets` |
| POST | `/customer-service/tickets/{ticket_id}/close` | `close_ticket` | `tickets` |
| POST | `/customer-service/tickets/{ticket_id}/reopen` | `reopen_ticket` | `tickets` |
| POST | `/customer-service/tickets/{ticket_id}/assign` | `assign_ticket` | `tickets` |
| POST | `/customer-service/tickets/{ticket_id}/auto-assign` | `auto_assign_ticket` | `tickets` |
| POST | `/customer-service/sla/policies` | `create_sla_policy` | `sla` |
| GET | `/customer-service/sla/policies` | `list_sla_policies` | `sla` |
| GET | `/customer-service/sla/violations` | `list_sla_violations` | `sla` |
| POST | `/customer-service/sla/check` | `check_sla_breaches` | `sla` |
| POST | `/customer-service/conversations/{conversation_id}/tags/` | `add_conversation_tag` | `tags` |
| GET | `/customer-service/conversations/{conversation_id}/tags/` | `list_conversation_tags` | `tags` |
| DELETE | `/customer-service/conversations/{conversation_id}/tags/{name}` | `remove_conversation_tag` | `tags` |
| GET | `/customer-service/audit-logs/` | `list_audit_logs` | `audit_logs` |
| POST | `/customer-service/macros/` | `create_macro` | `macros` |
| GET | `/customer-service/macros/` | `list_macros` | `macros` |
| PATCH | `/customer-service/macros/{macro_id}` | `update_macro` | `macros` |
| POST | `/customer-service/macros/{macro_id}/apply/{conversation_id}` | `apply_macro` | `macros` |
| POST | `/customer-service/conversations/{conversation_id}/intelligence/analyze` | `analyze_conversation` | `conversation_intelligence` |
| GET | `/customer-service/conversations/{conversation_id}/intelligence` | `list_conversation_insights` | `conversation_intelligence` |
| GET | `/customer-service/conversations/{conversation_id}/intelligence/snapshot` | `get_conversation_intelligence_snapshot` | `conversation_intelligence_snapshot` |
| POST | `/customer-service/conversations/{conversation_id}/suggested-actions/generate` | `generate` | `suggested_actions` |
| GET | `/customer-service/conversations/{conversation_id}/suggested-actions` | `list_actions` | `suggested_actions` |
| POST | `/customer-service/suggested-actions/{action_id}/accept` | `accept_action` | `suggested_actions` |
| POST | `/customer-service/suggested-actions/{action_id}/reject` | `reject_action` | `suggested_actions` |
| POST | `/customer-service/suggested-actions/{action_id}/execute` | `execute_action` | `suggested_actions` |
| POST | `/customer-service/conversations/{conversation_id}/reply-quality` | `record_reply_quality` | `reply_quality` |
| GET | `/customer-service/conversations/{conversation_id}/reply-quality` | `list_reply_quality` | `reply_quality` |
| GET | `/customer-service/analytics/reply-quality` | `reply_quality_analytics` | `reply_quality` |
| GET | `/customer-service/analytics/reply-quality/insights` | `reply_quality_insights` | `reply_quality_insights` |
| GET | `/customer-service/analytics/reply-quality/dashboard` | `reply_quality_dashboard` | `reply_quality_dashboard` |
| GET | `/customer-service/analytics/reply-quality/trends` | `reply_quality_trends` | `reply_quality_trends` |
| POST | `/customer-service/conversations/{conversation_id}/quality-review` | `review` | `quality_reviews` |
| GET | `/customer-service/conversations/{conversation_id}/quality-review` | `list_reviews` | `quality_reviews` |
| POST | `/customer-service/workflow-templates` | `create_template` | `workflow_templates` |
| GET | `/customer-service/workflow-templates` | `list_templates` | `workflow_templates` |
| POST | `/customer-service/workflow-templates/seed-shopify` | `seed_shopify_templates` | `workflow_templates` |
| POST | `/customer-service/workflow-templates/{template_id}/clone` | `clone_template` | `workflow_templates` |
| PATCH | `/customer-service/workflow-templates/{template_id}` | `update_template` | `workflow_templates` |
| POST | `/customer-service/workflow-templates/{template_id}/publish` | `publish_template` | `workflow_templates` |
| POST | `/customer-service/workflow-templates/{template_id}/unpublish` | `unpublish_template` | `workflow_templates` |
| POST | `/customer-service/workflow-templates/seed-website-chat` | `seed_website_chat_workflow_templates` | `workflow_templates` |
| GET | `/customer-service/workflow-executions` | `list_workflow_executions` | `workflow_executions` |
| GET | `/customer-service/workflow-executions/{job_id}` | `get_workflow_execution` | `workflow_executions` |
| GET | `/customer-service/conversations/{conversation_id}/workflow-executions` | `list_conversation_workflow_executions` | `workflow_executions` |
| GET | `/customer-service/tickets/{ticket_id}/workflow-executions` | `list_ticket_workflow_executions` | `workflow_executions` |
| POST | `/customer-service/conversations/{conversation_id}/ai-replies/compose` | `compose_ai_reply` | `ai_replies` |
| POST | `/customer-service/conversations/{conversation_id}/ai-replies/regenerate` | `regenerate_ai_reply` | `ai_replies` |
| POST | `/customer-service/conversations/{conversation_id}/summary/generate` | `generate_conversation_summary` | `ai_replies` |
| POST | `/customer-service/knowledge/search` | `search_knowledge` | `knowledge` |
| POST | `/customer-service/shopify/connect` | `connect_shopify` | `shopify` |
| GET | `/customer-service/shopify/orders/{order_ref}` | `get_order` | `shopify` |
| POST | `/customer-service/shopify/orders/{order_ref}/actions/{action}` | `perform_order_action` | `shopify` |
| POST | `/customer-service/shopify/support-workflows/prepare` | `prepare_support_workflow` | `shopify` |
| POST | `/customer-service/shopify/install` | `start_shopify_install` | `shopify` |
| GET | `/customer-service/shopify/install` | `start_shopify_install_redirect` | `shopify` |
| GET | `/customer-service/shopify/oauth/callback` | `shopify_oauth_callback` | `shopify` |
| POST | `/customer-service/shipping/track` | `track_shipping` | `shipping` |
| GET | `/customer-service/omnichannel/connections` | `list_channel_connections` | `omnichannel` |
| POST | `/customer-service/omnichannel/connections` | `create_channel_connection` | `omnichannel` |
| POST | `/customer-service/omnichannel/inbound` | `ingest_inbound_message` | `omnichannel` |
| POST | `/customer-service/omnichannel/outbound` | `send_outbound_message` | `omnichannel` |
| POST | `/customer-service/omnichannel/delivery-events` | `apply_delivery_event` | `omnichannel` |
| GET | `/customer-service/omnichannel/providers/capabilities` | `list_provider_capabilities` | `omnichannel` |
| POST | `/customer-service/omnichannel/outbound/enqueue` | `enqueue_outbound_message` | `omnichannel` |
| POST | `/customer-service/event-subscriptions` | `create_event_subscription` | `event_subscriptions` |
| GET | `/customer-service/event-subscriptions` | `list_event_subscriptions` | `event_subscriptions` |
| GET | `/customer-service/event-subscriptions/{subscription_id}` | `get_event_subscription` | `event_subscriptions` |
| PATCH | `/customer-service/event-subscriptions/{subscription_id}` | `update_event_subscription` | `event_subscriptions` |
| DELETE | `/customer-service/event-subscriptions/{subscription_id}` | `delete_event_subscription` | `event_subscriptions` |
| POST | `/customer-service/event-subscriptions/seed-shopify` | `seed_shopify_event_subscriptions` | `event_subscriptions` |
| POST | `/customer-service/event-subscriptions/{subscription_id}/enable` | `enable_event_subscription` | `event_subscriptions` |
| POST | `/customer-service/event-subscriptions/{subscription_id}/disable` | `disable_event_subscription` | `event_subscriptions` |
| POST | `/customer-service/routing-policies` | `create_routing_policy` | `routing_policies` |
| GET | `/customer-service/routing-policies` | `list_routing_policies` | `routing_policies` |
| GET | `/customer-service/routing-policies/{policy_id}` | `get_routing_policy` | `routing_policies` |
| PATCH | `/customer-service/routing-policies/{policy_id}` | `update_routing_policy` | `routing_policies` |
| DELETE | `/customer-service/routing-policies/{policy_id}` | `delete_routing_policy` | `routing_policies` |
| POST | `/customer-service/agents` | `create_agent` | `agents` |
| GET | `/customer-service/agents` | `list_agents` | `agents` |
| GET | `/customer-service/agents/{agent_id}` | `get_agent` | `agents` |
| PATCH | `/customer-service/agents/{agent_id}` | `update_agent` | `agents` |
| DELETE | `/customer-service/agents/{agent_id}` | `delete_agent` | `agents` |
| POST | `/customer-service/teams` | `create_team` | `teams` |
| GET | `/customer-service/teams` | `list_teams` | `teams` |
| GET | `/customer-service/teams/{team_id}` | `get_team` | `teams` |
| PATCH | `/customer-service/teams/{team_id}` | `update_team` | `teams` |
| DELETE | `/customer-service/teams/{team_id}` | `delete_team` | `teams` |
| POST | `/customer-service/teams/{team_id}/members` | `add_team_member` | `teams` |
| DELETE | `/customer-service/teams/{team_id}/members/{agent_id}` | `remove_team_member` | `teams` |
| POST | `/customer-service/queues` | `create_queue` | `queues` |
| GET | `/customer-service/queues` | `list_queues` | `queues` |
| GET | `/customer-service/queues/{queue_id}` | `get_queue` | `queues` |
| PATCH | `/customer-service/queues/{queue_id}` | `update_queue` | `queues` |
| DELETE | `/customer-service/queues/{queue_id}` | `delete_queue` | `queues` |
| POST | `/customer-service/chat/sessions` | `create_session` | `chat_router` |
| POST | `/customer-service/chat/sessions/{session_id}/messages` | `create_message` | `chat_router` |
| GET | `/customer-service/chat/sessions/{session_id}/messages` | `list_messages` | `chat_router` |
| GET | `/customer-service/chat/widget/settings` | `get_widget_settings` | `chat_router` |
| PUT | `/customer-service/chat/widget/settings` | `update_widget_settings` | `chat_router` |
| GET | `/customer-service/chat/public/{public_key}/settings` | `get_public_widget_settings` | `chat_router` |
| POST | `/customer-service/chat/public/{public_key}/sessions` | `create_public_session` | `chat_router` |
| POST | `/customer-service/chat/public/{public_key}/sessions/{session_id}/messages` | `create_public_message` | `chat_router` |
| GET | `/customer-service/chat/public/{public_key}/sessions/{session_id}/messages` | `list_public_messages` | `chat_router` |
| GET | `/customer-service/conversations/{conversation_id}/timeline` | `get_conversation_timeline` | `timeline` |
| GET | `/customer-service/conversations/{conversation_id}/context` | `get_conversation_context` | `conversation_context` |
| GET | `/customer-service/conversations/{conversation_id}/workspace-recommendations` | `get_workspace_recommendations` | `workspace_recommendations` |
| POST | `/customer-service/webhooks/omnichannel` | `ingest_omnichannel_webhook` | `webhooks` |

---

# 7. Frontend product map

This section maps backend capability to frontend pages/components.

## 7.1 App shell / auth

Use `/signup`, `/login`, `/refresh`, `/logout`, `/me` from `app/routers/auth.py`. Frontend should centralize auth token/session handling and attach auth headers to protected API calls.

## 7.2 Inbox page

Primary endpoints:

- `GET /customer-service/inbox/`
- `GET /customer-service/conversations/{conversation_id}`
- `GET /customer-service/conversations/{conversation_id}/messages?limit=&offset=`
- `POST /customer-service/conversations/{conversation_id}/messages`
- `POST /customer-service/conversations/{conversation_id}/internal-notes`
- `GET /customer-service/conversations/{conversation_id}/context`
- `GET /customer-service/conversations/{conversation_id}/timeline`

Frontend should load inbox list with pagination, selected conversation detail, paginated message history, context sidebar, and timeline/activity panels.

## 7.3 Ticket sidebar / support CRM

Primary endpoints:

- `GET /customer-service/tickets/`
- `GET /customer-service/tickets/{ticket_id}`
- `PATCH /customer-service/tickets/{ticket_id}`
- `POST /customer-service/tickets/{ticket_id}/close`
- `POST /customer-service/tickets/{ticket_id}/reopen`
- `POST /customer-service/tickets/{ticket_id}/assign`
- `POST /customer-service/tickets/{ticket_id}/auto-assign`
- `GET /customer-service/customers/{customer_id}/360`
- `GET /customer-service/customers/{customer_id}/activity`
- `GET /customer-service/customers/{customer_id}/risk`

Show customer identity, ticket state, SLA, tags, Shopify/order context, risk and recommendations.

## 7.4 AI assist / agent assist

Primary endpoints:

- `POST /customer-service/conversations/{conversation_id}/ai-replies/compose`
- `POST /customer-service/conversations/{conversation_id}/ai-replies/regenerate`
- `POST /customer-service/conversations/{conversation_id}/agent-assist/reply-suggestion`
- `GET /customer-service/conversations/{conversation_id}/agent-assist/suggestions`
- `PATCH /customer-service/conversations/agent-assist/suggestions/{suggestion_id}`
- `POST /customer-service/conversations/agent-assist/suggestions/{suggestion_id}/approve`
- `POST /customer-service/conversations/agent-assist/suggestions/{suggestion_id}/reject`
- `POST /customer-service/conversations/agent-assist/suggestions/{suggestion_id}/send`
- `GET /customer-service/conversations/agent-assist/suggestions/{suggestion_id}/revisions`

Model-facing features use `CustomerServiceAIContextPolicy`; frontend does not need to send full conversation history.

## 7.5 Website chat widget

Primary endpoints:

- `GET /customer-service/chat/widget/settings`
- `PUT /customer-service/chat/widget/settings`
- `GET /customer-service/chat/public/{public_key}/settings`
- `POST /customer-service/chat/public/{public_key}/sessions`
- `POST /customer-service/chat/public/{public_key}/sessions/{session_id}/messages`
- `GET /customer-service/chat/public/{public_key}/sessions/{session_id}/messages`

Use these for merchant widget settings, public embedded chat, and inbox bridge.

## 7.6 Omnichannel / external channels

Primary endpoints:

- `GET /customer-service/omnichannel/connections`
- `POST /customer-service/omnichannel/connections`
- `POST /customer-service/omnichannel/inbound`
- `POST /customer-service/omnichannel/outbound`
- `POST /customer-service/omnichannel/outbound/enqueue`
- `POST /customer-service/omnichannel/delivery-events`
- `GET /customer-service/omnichannel/providers/capabilities`

Use these for channel connection setup, capability display, inbound testing, outbound actions and delivery status.

## 7.7 Shopify/ecommerce actions

Primary endpoints:

- `POST /customer-service/shopify/connect`
- `GET /customer-service/shopify/orders/{order_ref}`
- `POST /customer-service/shopify/orders/{order_ref}/actions/{action}`
- `POST /customer-service/shopify/support-workflows/prepare`
- Shopify OAuth install/callback endpoints

Frontend surfaces: Shopify connection setup, order lookup panel, safe action workflow preview, and approval UX before risky operations. Shopify tokens are encrypted at rest and order action idempotency is supported.

## 7.8 Routing, teams, agents, queues

Primary endpoints: `/customer-service/agents`, `/customer-service/teams`, `/customer-service/queues`, `/customer-service/routing-policies`, plus ticket auto-assign.

Frontend surfaces: agent management, team management, queue management, routing policy builder, assignment/debug panel.

## 7.9 SLA and quality

Primary endpoints:

- `/customer-service/sla/policies`
- `/customer-service/sla/violations`
- `/customer-service/sla/check`
- `/customer-service/conversations/{conversation_id}/reply-quality`
- `/customer-service/analytics/reply-quality`
- `/customer-service/analytics/reply-quality/insights`
- `/customer-service/analytics/reply-quality/dashboard`
- `/customer-service/analytics/reply-quality/trends`
- `/customer-service/conversations/{conversation_id}/quality-review`

Frontend surfaces: SLA configuration, SLA widgets, quality dashboard, reply review panels, agent coaching insights.

## 7.10 Workflow builder and operations UI

Core workflow endpoints are spread across `app/routers/workflows.py`, `app/routers/workflows_route/*`, `app/workflow_operations/*/router.py`, `app/jobs/router.py`, `app/schedules/router.py`, and `app/platform/events/router.py`.

Frontend should provide workflow builder, node catalog, validate/run/resume controls, run detail, event stream/timeline, snapshots/replay/diff, versions, deployments, evaluations, job queue/DLQ/metrics, and schedule management.

---

# 8. Development guide: where to add new work

## Add a new customer-service API feature

1. Add/modify ORM model in `domains/customer_service/models/*` if data model changes.
2. Add migration.
3. Add Pydantic contracts in `schemas/*`.
4. Add repository methods in `repositories/*`.
5. Add business logic in `services/*`.
6. Add route in `routers/*`.
7. Register route in `domains/customer_service/main.py` if it is a new router file.
8. Add tests under `tests/customer_service/...`.

## Add a new workflow node

1. Define config/schema in `runtime/catalog/schemas.py` or node-specific module.
2. Implement node in `runtime/catalog/nodes/*` or `runtime/nodes/*` depending on runtime layer.
3. Register in `runtime/catalog/builtins.py` or node registry.
4. Add frontend catalog metadata if needed.
5. Add tests for validation and execution.

## Add a long-running/retryable operation

Use jobs when the operation is slow, retryable, an external side effect, must survive process restart, or should not block request/response.

Implementation path:

1. Create service method to enqueue via `JobService`.
2. Add job handler and register in `jobs/handlers.py` or domain job registration module.
3. Add idempotency key where duplicate execution is dangerous.
4. Add DLQ/retry tests.

## Add a new external channel/provider

1. Implement provider adapter under `domains/customer_service/integrations/omnichannel/` or `webhooks/providers/`.
2. Register provider in registry.
3. Add schemas if provider-specific fields are needed.
4. Use `CustomerServiceOmnichannelService` for inbound/outbound flow.
5. Add signature verification if public webhooks are involved.

## Add a new AI/customer-service feature

Rules:

- Do not load full `conversation.messages` for model prompts.
- Use `ConversationRepository.list_recent_context_messages(...)`.
- Respect `CustomerServiceAIContextPolicy`.
- Keep UI history pagination separate from model context.

Recommended layers:

```text
router → service → repository/provider/job/event
```

---

# 9. Important architecture decisions already present

## Bounded AI context

Model-facing features use bounded recent message context rather than full history. This protects cost, latency, memory, and token usage.

## Paginated conversation messages

Full conversation history is available through paginated message endpoints. UI can load history independently of model prompts.

## Router centralization

- `app/main.py` includes only `api_router`.
- `app/routers/main.py` composes app-level routers.
- `domains/customer_service/main.py` composes domain routers.

## Customer-service route safety

Tests protect duplicate customer-service routes and important route presence.

## Durable job boundary

External side effects and workflow execution are job-backed. Derived read views remain live-computed but bounded until scale requires snapshots.

## Compatibility re-exports

`domains/customer_service/models/models.py` keeps backward import compatibility while models are split by responsibility.

---

# 10. Recommended next docs for frontend team

For frontend implementation, create these separate API reference documents later:

1. Inbox API contract
2. Conversation detail/message/timeline/context contract
3. Chat widget public API contract
4. Shopify support action contract
5. Workflow builder/run/debug contract
6. Routing/SLA/team management contract
7. Agent assist/reply quality contract

This document is the system map. Those follow-up docs should become endpoint-by-endpoint API references with request/response examples.
