from __future__ import annotations

from app.runtime.nodes.registry import register_node

from app.runtime.nodes.configs import (
    TriggerMessageConfig,
    AgentLangGraphConfig,
    AgentMCPConfig,
    RouterRulesConfig,
    RouterLLMConfig,
    JoinAllConfig,
    ResponseConfig,
    SetVariableConfig,
)
from app.runtime.nodes.builtins.trigger_message import TriggerMessageNode
from app.runtime.nodes.builtins.agent_langgraph import AgentLangGraphNode
from app.runtime.nodes.builtins.agent_mcp import AgentMCPNode
from app.runtime.nodes.builtins.router_rules import RouterRulesNode
from app.runtime.nodes.builtins.router_llm import RouterLLMNode
from app.runtime.nodes.builtins.join_all import JoinAllNode
from app.runtime.nodes.builtins.response import ResponseNode
from app.runtime.nodes.builtins.set_variable import SetVariableNode
from app.runtime.nodes.builtins.human_approval import HumanApprovalNode
from app.runtime.nodes.configs import (
    HumanApprovalConfig,
    WaitTimeConfig,
    WaitEventConfig,
)
from app.runtime.nodes.configs import SubworkflowCallConfig
from app.runtime.nodes.builtins.subworkflow_call import SubworkflowCallNode
from app.runtime.nodes.configs import LoopConfig
from app.runtime.nodes.builtins.control_loop import ControlLoopNode
from app.runtime.nodes.builtins.web_search import WebSearchNode, WebSearchConfig
from app.runtime.nodes.builtins.web_fetch_extract import (
    WebFetchExtractNode,
    WebFetchExtractConfig,
)
from app.runtime.nodes.builtins.knowledge_ingest import (
    KnowledgeIngestNode,
    KnowledgeIngestConfig,
)
from app.runtime.nodes.builtins.knowledge_search import (
    KnowledgeSearchNode,
    KnowledgeSearchConfig,
)
from app.runtime.nodes.builtins.llm_generate import LlmGenerateNode, LlmGenerateConfig
from app.runtime.nodes.builtins.platform_job import (
    PlatformJobEnqueueNode,
    PlatformJobEnqueueConfig,
)
from app.runtime.nodes.builtins.capability import CapabilityInvokeNode, CapabilityInvokeConfig
from app.runtime.nodes.builtins.context_extract import (
    ContextExtractNode,
    ContextExtractConfig,
)
from app.agents_runtime.config import AgentCustomConfig
from app.runtime.nodes.builtins.agent_custom import AgentCustomNode
from app.runtime.nodes.builtins.wait_time import WaitTimeNode
from app.runtime.nodes.builtins.wait_event import WaitEventNode


def register_core_nodes() -> None:
    """
    Register generic workflow node types owned by the core runtime.

    This function is called during FastAPI app startup/lifespan before workflows_route
    are executed. It connects frontend nodeType strings to backend Python node
    classes and Pydantic config models.

    Runtime flow:
        workflow node.data.nodeType
            -> get_node(nodeType)
            -> NodeRegistration
            -> node_cls()
            -> config_model.model_validate(...)
            -> node.run(...)

    Example:
        register_core_nodes()

        # Later, a workflow node with:
        # {"nodeType": "response"}
        #
        # resolves to:
        # ResponseNode + ResponseConfig
    """
    register_node("trigger.message", TriggerMessageNode, TriggerMessageConfig)
    # register_node("kb.search", KBSearchNode, KBSearchConfig)
    register_node("agent.custom", AgentCustomNode, AgentCustomConfig)
    register_node("agent.langgraph", AgentLangGraphNode, AgentLangGraphConfig)
    register_node("agent.mcp", AgentMCPNode, AgentMCPConfig)
    register_node("router.rules", RouterRulesNode, RouterRulesConfig)
    register_node("router.llm", RouterLLMNode, RouterLLMConfig)
    register_node("join.all", JoinAllNode, JoinAllConfig)
    register_node("response", ResponseNode, ResponseConfig)
    register_node("set.variable", SetVariableNode, SetVariableConfig)
    register_node(
        "human.approval",
        HumanApprovalNode,
        HumanApprovalConfig,
        risk_level="sensitive",
        requires_approval=True,
    )
    register_node("wait.time", WaitTimeNode, WaitTimeConfig)
    register_node("wait.event", WaitEventNode, WaitEventConfig)
    register_node("subworkflow.call", SubworkflowCallNode, SubworkflowCallConfig)
    register_node("control.loop", ControlLoopNode, LoopConfig)
    register_node("web.search", WebSearchNode, WebSearchConfig)
    register_node("web.fetch_extract", WebFetchExtractNode, WebFetchExtractConfig)
    register_node(
        "knowledge.ingest",
        KnowledgeIngestNode,
        KnowledgeIngestConfig,
        risk_level="sensitive",
        side_effect=True,
        replay_policy="skip",
    )
    register_node("kb.search", KnowledgeSearchNode, KnowledgeSearchConfig)
    register_node("llm.generate", LlmGenerateNode, LlmGenerateConfig)
    register_node(
        "platform.job.enqueue",
        PlatformJobEnqueueNode,
        PlatformJobEnqueueConfig,
        risk_level="sensitive",
        side_effect=True,
        replay_policy="skip",
    )
    register_node("context.extract", ContextExtractNode, ContextExtractConfig)

    register_node("capability.invoke", CapabilityInvokeNode, CapabilityInvokeConfig)



def register_builtin_nodes() -> None:
    """
    Backward-compatible name for registering core runtime nodes.

    Product and provider nodes are composed at the application boundary.
    """

    register_core_nodes()


__all__ = [
    "register_builtin_nodes",
    "register_core_nodes",
]
