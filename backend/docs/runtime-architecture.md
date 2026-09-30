# Tajeran Runtime Architecture

## 1. Big Picture

Tajeran runtime is a custom workflow orchestration engine.

React Flow is the visual builder.
FastAPI receives the workflow JSON.
The runtime engine executes the workflow node by node.

LangGraph is optional. It can run inside one node, but it does not control the whole workflow.

```text
Frontend React Flow
        |
        v
/workflows_route/run
        |
        v
RuntimeContext
        |
        v
execute_workflow_dag()
        |
        v
Custom Tajeran Runtime Engine
        |
        v
Nodes
        |
        +--> kb.search
        +--> llm.generate
        +--> router.rules
        +--> human.approval
        +--> agent.langgraph optional
        +--> agent.mcp optional
        +--> response

```
## Reasoning Architecture
```text
Customer message
      |
      v
Context Collector
      |
      v
Policy / Knowledge Retriever
      |
      v
Reasoning Agent
      |
      v
Critic / Verifier
      |
      v
Decision Router
      |
      v
Action / Response
```

```text
Best Practice for Reasoning Nodes
small specialized nodes + shared state + verifier
Use several specialized nodes:
1. classify.intent
2. retrieve.context
3. reason.answer
4. verify.answer
5. route.decision
6. response
```
## Production Mental Model

- Is this orchestration logic?

```text
Put it in:
app/runtime/engine/

Examples:
pause/resume
routing
loop
scheduler
execution policy
deadlock
parallelism
```
- Is this a new workflow action?
```text
Put it in:
app/runtime/catalog/nodes/
or
app/runtime/nodes/

Examples:
shopify.get_order
shopify.refund_order
email.send
ticket.create
reason.verify
```
- Is this API route logic?
```text
Put it in:
app/routers/workflows_route/

Examples:
run workflow
resume workflow
stream events
list runs
save workflow
```
- Is this state helper logic?
- ```text
Put it in:
app/runtime/state/
Examples:
new state
snapshot
patch merge
```