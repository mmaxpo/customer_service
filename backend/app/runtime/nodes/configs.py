from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, model_validator, Field


"""
Pydantic config schemas for built-in workflow nodes.

These schemas define the contract between:
    - React Flow frontend node configs
    - backend node execution
    - registry/default config generation

Runtime flow:
    workflow node.data
        -> render_template(...)
        -> parse_node_config(...)
        -> Pydantic schema validation
        -> node.run(ctx, state, config)

Every node config should describe:
    - node_type
    - user-configurable fields
    - runtime hardening fields when appropriate
"""


class BaseNodeConfig(BaseModel):
    """
    Shared config fields for most workflow nodes.

    Provides:
        - human-readable name
        - save_as support
        - timeout/retry execution controls

    Example:
        {
            "nodeType": "kb.search",
            "name": "Search refund policy",
            "save_as": "kb_hits",
            "timeout_ms": 5000,
            "retries": 2,
            "retry_backoff_ms": 200
        }
    """

    name: Optional[str] = Field(default=None, description="Human readable name")
    save_as: Optional[str] = Field(
        default=None, description="Store output into state.vars[save_as]"
    )

    # ✅ Layer 1.2 hardening
    timeout_ms: Optional[int] = Field(
        default=None, ge=1, description="Per-node timeout in ms"
    )
    retries: int = Field(default=0, ge=0, le=10, description="Retry count on failure")
    retry_backoff_ms: int = Field(
        default=0, ge=0, le=60_000, description="Backoff between retries in ms"
    )


class TriggerMessageConfig(BaseNodeConfig):
    """
    Config for trigger.message node.

    The trigger node starts a workflow and usually writes the initial message
    into state.

    Example:
        {
            "nodeType": "trigger.message",
            "input": "Where is my order?"
        }
    """

    node_type: Literal["trigger.message"] = "trigger.message"
    input: str = Field(
        default="", description="Initial message (prompt) to start workflow"
    )


class KBSearchConfig(BaseNodeConfig):
    """
    Config for knowledge-base search node.

    The node reads a query either from:
        - state["last"]
        - state["vars"][query_key]

    Example:
        {
            "nodeType": "kb.search",
            "query_from": "last",
            "top_k": 5,
            "save_as": "kb_hits"
        }
    """

    node_type: Literal["kb.search"] = "kb.search"
    top_k: int = Field(default=5, ge=1, le=50)
    # where to read query from:
    query_from: Literal["last", "vars"] = Field(default="last")
    query_key: str = Field(
        default="input",
        description="If query_from=vars, read from state.vars[query_key]",
    )


class SetVariableConfig(BaseNodeConfig):
    """
    Config for set.variable node.

    This node writes a JSON value into state.vars[key].

    Example:
        {
            "nodeType": "set.variable",
            "key": "intent",
            "value": "refund"
        }
    """

    node_type: Literal["set.variable"] = "set.variable"
    key: str = Field(..., description="state.vars[key] = value")
    value: Any = Field(..., description="Any JSON value")


class AgentLangGraphConfig(BaseNodeConfig):
    """
    Config for agent.langgraph node.

    This node delegates an internal reasoning/tool workflow to LangGraph while
    your runtime remains the outer orchestration layer.

    Example:
        {
            "nodeType": "agent.langgraph",
            "system_prompt": "You are a support agent.",
            "input_from": "last"
        }
    """

    node_type: Literal["agent.langgraph"] = "agent.langgraph"
    system_prompt: Optional[str] = Field(
        default=None, description="Optional system prompt override"
    )
    input_from: Literal["last", "vars"] = Field(default="last")
    input_key: str = Field(default="input")


class AgentMCPConfig(BaseNodeConfig):
    """
    Config for agent.mcp node.

    This node lets an agent use tools exposed through MCP servers.

    Example:
        {
            "nodeType": "agent.mcp",
            "system_prompt": "Use available tools to solve the request.",
            "input_from": "last"
        }
    """

    node_type: Literal["agent.mcp"] = "agent.mcp"
    system_prompt: Optional[str] = Field(default=None)
    input_from: Literal["last", "vars"] = Field(default="last")
    input_key: str = Field(default="input")


class Rule(BaseModel):
    """
    One rule for router.rules.

    If the condition matches, the router emits the configured route key.

    Example:
        {
            "when": "vars.intent == 'billing'",
            "route": "billing"
        }
    """

    when: str = Field(
        ...,
        description="Expression string. For MVP support: equals check like `vars.intent == 'billing'`",
    )
    route: str = Field(..., description="Route key to emit when rule matches")


class RouterRulesConfig(BaseNodeConfig):
    """
    Config for rule-based router node.

    The router evaluates rules and emits a route key. Conditional edges can then
    use that route to choose the next path.

    Example:
        {
            "nodeType": "router.rules",
            "rules": [
                {"when": "vars.intent == 'refund'", "route": "refund"}
            ],
            "default_route": "default"
        }
    """

    node_type: Literal["router.rules"] = "router.rules"
    rules: List[Rule] = Field(default_factory=list)
    default_route: str = Field(default="default")


class RouterLLMConfig(BaseNodeConfig):
    """
    Config for LLM-based router node.

    The LLM chooses one route key from allowed choices.

    Example:
        {
            "nodeType": "router.llm",
            "choices": ["refund", "shipping", "default"],
            "instruction": "Choose the best route.",
            "input_from": "last"
        }
    """

    node_type: Literal["router.llm"] = "router.llm"
    choices: List[str] = Field(..., min_length=2, description="Allowed route keys")
    instruction: str = Field(
        default="Choose the best route for the user request. Output ONLY the route key.",
        description="Router prompt/instruction",
    )
    input_from: Literal["last", "vars"] = Field(default="last")
    input_key: str = Field(default="input")


class JoinAllConfig(BaseNodeConfig):
    """
    Config for join.all node.

    This node combines outputs from multiple parent nodes.

    Modes:
        list:
            returns parent outputs as a list

        concat_text:
            converts parent outputs to text and joins them with separator

    Example:
        {
            "nodeType": "join.all",
            "mode": "concat_text",
            "separator": "\\n---\\n"
        }
    """

    node_type: Literal["join.all"] = "join.all"
    # How to combine inputs from multiple parents:
    mode: Literal["list", "concat_text", "object"] = Field(default="object")
    separator: str = Field(default="\n")


class ResponseConfig(BaseNodeConfig):
    @model_validator(mode="before")
    @classmethod
    def unwrap_nested_runtime_config(cls, data):
        if isinstance(data, dict) and isinstance(data.get("config"), dict):
            merged = dict(data)
            nested = dict(merged.pop("config"))
            nested.setdefault(
                "node_type",
                merged.get("nodeType") or merged.get("node_type") or "response",
            )
            return nested
        return data

    """
    Config for response node.

    This node produces the final workflow answer.

    It can read from:
        - state["last"]
        - state["vars"][answer_key]
        - state["vars"] path via from_var

    Example:
        {
            "answer_from": "last"
        }

    Example using variable:
        {
            "answer_from": "vars",
            "answer_key": "final_answer"
        }
    """

    answer_from: Literal["last", "vars"] = "last"
    answer_key: str = "answer"
    save_as: Optional[str] = None
    raw: bool = False
    from_var: Optional[str] = None  # e.g. "ws" or "ws.results.0.title"
    as_json: bool = False  # if True, json.dumps(answer)


class HumanApprovalConfig(BaseNodeConfig):
    """
    Config for human.approval node.

    This node pauses workflow execution until a human/user provides resume input.

    Resume flow:
        executor injects ctx.extras["resume_input"] into:
            state["vars"]["resume_input"]

        node reads:
            state["vars"][input_key][field]

    Example:
        {
            "question": "Approve refund?",
            "input_key": "resume_input",
            "field": "approved",
            "save_as": "approved"
        }
    """

    question: str = Field("Approve?", min_length=1)

    # Where resume payload is injected by executor (/workflows_route/resume):
    input_key: str = Field("resume_input")

    # Field inside resume_input to read:
    field: str = Field("approved")

    # Optional: save result into state.vars[save_as]
    save_as: str | None = None

    # Optional state.vars key whose value should be copied into the durable
    # approval wait and interrupt payload. This lets reviewers see exactly
    # what they are approving without adding domain logic to this node.
    context_key: str | None = None

    # Payload field used when context_key is configured.
    context_payload_key: str = Field(
        default="context",
        min_length=1,
    )


class SubworkflowCallConfig(BaseNodeConfig):
    """
    Config for subworkflow.call node.

    This node executes an inline child workflow and returns the child result.

    Example:
        {
            "nodeType": "subworkflow.call",
            "workflow": {
                "nodes": [...],
                "edges": [...]
            },
            "input_from": "last",
            "include_child_meta": false
        }
    """

    node_type: Literal["subworkflow.call"] = "subworkflow.call"

    # Inline child workflow JSON
    workflow: Dict[str, Any] = Field(
        ..., description="Child workflow JSON {nodes, edges}"
    )

    # How to pick the input to feed child trigger.message input
    input_from: Literal["last", "vars"] = Field(default="last")
    input_key: str = Field(default="input")

    # If true, attach child meta in this node's meta (can be heavy)
    include_child_meta: bool = Field(default=False)


class LoopConfig(BaseNodeConfig):
    """
    Config for control.loop node.

    This node creates a controlled cycle by deciding whether to continue or stop.

    It tracks iteration count in:
        state["vars"][loop_key]

    When continuing, the executor resets reset_node_ids so those nodes can run
    again.

    Example:
        {
            "nodeType": "control.loop",
            "loop_key": "retry_count",
            "max_iters": 3,
            "reset_node_ids": ["llm_generate", "judge"],
            "continue_route": "continue",
            "stop_route": "stop"
        }
    """

    node_type: Literal["control.loop"] = "control.loop"

    # store loop counter in vars[loop_key]
    loop_key: str = Field(default="loop_count", min_length=1)

    # maximum number of continues before stopping
    max_iters: int = Field(default=3, ge=1, le=100)

    # which node ids to "rewind" when continuing
    reset_node_ids: List[str] = Field(default_factory=list, min_length=1)

    # route keys (so UI stays consistent)
    continue_route: str = Field(default="continue", min_length=1)
    stop_route: str = Field(default="stop", min_length=1)


class WaitTimeConfig(BaseNodeConfig):
    """Config for wait.time node."""

    nodeType: Literal["wait.time"] = "wait.time"

    seconds: int = Field(
        default=60,
        ge=1,
        description="How many seconds to wait before resuming workflow.",
    )

    reason: str | None = None


class WaitEventConfig(BaseNodeConfig):
    """Config for wait.event node."""

    nodeType: Literal["wait.event"] = "wait.event"

    event_type: str = Field(
        ...,
        min_length=1,
        description="Platform event type that should resume this workflow.",
    )

    match: dict = Field(
        default_factory=dict,
        description="Optional key/value match against event payload.",
    )

    reason: str | None = None
