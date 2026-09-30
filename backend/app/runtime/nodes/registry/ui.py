from __future__ import annotations

from typing import Dict

NODE_UI: Dict[str, Dict[str, str]] = {
    "trigger.message": {
        "title": "Message Trigger",
        "icon": "trigger",
        "category": "trigger",
        "group": "Core",
    },
    "kb.search": {
        "title": "Knowledge Search",
        "icon": "book",
        "category": "knowledge",
        "group": "Data",
    },
    "agent.custom": {
        "title": "Custom Agent",
        "icon": "bot",
        "category": "agent",
        "group": "AI",
    },
    "agent.langgraph": {
        "title": "Agent (LangGraph)",
        "icon": "bot",
        "category": "agent",
        "group": "AI",
    },
    "agent.mcp": {
        "title": "Agent (MCP)",
        "icon": "tool",
        "category": "agent",
        "group": "AI",
    },
    "router.rules": {
        "title": "Router (Rules)",
        "icon": "route",
        "category": "routing",
        "group": "AI",
    },
    "router.llm": {
        "title": "Router (LLM)",
        "icon": "sparkles",
        "category": "routing",
        "group": "AI",
    },
    "join.all": {
        "title": "Join (All)",
        "icon": "merge",
        "category": "control",
        "group": "Control",
    },
    "control.loop": {
        "title": "Loop (Controlled)",
        "icon": "repeat",
        "category": "control",
        "group": "Control",
    },
    "wait.event": {
        "title": "Wait Event",
        "icon": "radio",
        "category": "control",
        "group": "Control",
    },
    "wait.time": {
        "title": "Wait Time",
        "icon": "clock",
        "category": "control",
        "group": "Control",
    },
    "human.approval": {
        "title": "Human Approval",
        "icon": "user-check",
        "category": "control",
        "group": "Control",
    },
    "subworkflow.call": {
        "title": "Subworkflow",
        "icon": "layers",
        "category": "control",
        "group": "Control",
    },
    "set.variable": {
        "title": "Set Variable",
        "icon": "variable",
        "category": "data",
        "group": "Data",
    },
    "response": {
        "title": "Response",
        "icon": "check",
        "category": "output",
        "group": "Output",
    },
    "web.search": {
        "title": "Web Search",
        "icon": "search",
        "category": "web",
        "group": "Web",
    },
    "web.fetch_extract": {
        "title": "Fetch & Extract",
        "icon": "globe",
        "category": "web",
        "group": "Web",
    },
    "knowledge.ingest": {
        "title": "Knowledge Ingest",
        "icon": "upload",
        "category": "knowledge",
        "group": "Data",
    },
    "platform.job.enqueue": {
        "title": "Enqueue Job",
        "icon": "clock",
        "category": "platform",
        "group": "Platform",
    },
}
