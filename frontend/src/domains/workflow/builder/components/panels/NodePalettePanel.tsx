import type { CatalogItem } from "@/domains/workflow/builder/types/catalog";
import type { AgentToolCatalogItem } from "@/platform/api";
import {
    Bot,
    CheckCircle2,
    Database,
    GitBranch,
    Globe,
    MessageCircle,
    MousePointerClick,
    Reply,
    Route,
    Search,
    Split,
    Variable,
} from "lucide-react";

type Props = {
    catalogStatus: string;
    groupedCatalog: Map<string, CatalogItem[]>;
    addNode: (item: CatalogItem) => void;
    agentTools?: AgentToolCatalogItem[];
    addToolNode?: (tool: AgentToolCatalogItem) => void;
};

const HIDDEN_NODE_TYPES = new Set([
    "agent.langgraph",
    "agent.mcp",
]);

const NODE_LABELS: Record<string, string> = {
    "trigger.message": "Customer Message",
    "agent.custom": "AI Agent",
    "router.rules": "Rules Router",
    "router.llm": "AI Router",
    "join.all": "Join Results",
    response: "Send Response",
    "set.variable": "Set Value",
    "human.approval": "Human Approval",
    "subworkflow.call": "Subworkflow",
    "control.loop": "Loop",
    "web.search": "Web Search",
    "web.fetch_extract": "Fetch Web Page",
    "knowledge.ingest": "Add Knowledge",
    "kb.search": "Search Knowledge",
    "llm.generate": "Generate Text",
};

const NODE_DESCRIPTIONS: Record<string, string> = {
    "trigger.message": "Start a workflow from a customer message.",
    "agent.custom": "Run an AI agent with tools and instructions.",
    "router.rules": "Route by deterministic business rules.",
    "router.llm": "Let AI choose the next path.",
    "join.all": "Merge outputs from parallel branches.",
    response: "Return the final answer.",
    "set.variable": "Save a value for later nodes.",
    "human.approval": "Pause and ask for human approval.",
    "web.search": "Search the web.",
    "web.fetch_extract": "Fetch and extract a web page.",
    "knowledge.ingest": "Add text into the knowledge base.",
    "kb.search": "Search your knowledge base.",
    "llm.generate": "Generate text with an LLM.",
};

const ICONS: Record<string, any> = {
    "trigger.message": MessageCircle,
    "agent.custom": Bot,
    "router.rules": Route,
    "router.llm": GitBranch,
    "join.all": Split,
    response: Reply,
    "set.variable": Variable,
    "human.approval": CheckCircle2,
    "web.search": Globe,
    "web.fetch_extract": MousePointerClick,
    "knowledge.ingest": Database,
    "kb.search": Search,
    "llm.generate": Bot,
};

function groupLabel(group: string) {
    return group
        .replaceAll("_", " ")
        .replaceAll(".", " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function nodeLabel(item: CatalogItem) {
    return NODE_LABELS[item.node_type] ?? item.title ?? item.node_type;
}

function nodeDescription(item: CatalogItem) {
    return NODE_DESCRIPTIONS[item.node_type] ?? item.node_type;
}

export default function NodePalettePanel({
                                             catalogStatus,
                                             groupedCatalog,
                                             addNode,
                                             agentTools = [],
                                             addToolNode,
                                         }: Props) {
    const visibleGroups = [...groupedCatalog.entries()]
        .map(([group, items]) => [
            group,
            items.filter((item) => !HIDDEN_NODE_TYPES.has(item.node_type)),
        ] as const)
.filter(([, items]) => items.length > 0);

    return (
        <aside className="w-72 shrink-0 overflow-auto border-r border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold text-slate-950">Nodes</div>
            <div className="mt-1 text-xs text-slate-500">
                {catalogStatus || "Choose a node to add it."}
            </div>

            <div className="mt-4 space-y-5">
                {agentTools.length > 0 && (

                    <div>

                        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">

                            Agent Tools

                        </div>

                        <div className="space-y-2">

                            {agentTools.map((tool) => (

                                <button

                                    key={tool.name}

                                    onClick={() => addToolNode?.(tool)}

                                    className="group w-full rounded-2xl border border-slate-200 bg-white p-3 text-left transition hover:border-slate-300 hover:bg-slate-50"

                                >

                                    <div className="text-sm font-semibold text-slate-950">

                                        {tool.title}

                                    </div>

                                    <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">

                                        {tool.description}

                                    </div>

                                </button>

                            ))}

                        </div>

                    </div>

                )}
                {visibleGroups.map(([group, items]) => (
                    <div key={group}>
                        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {groupLabel(group)}
                        </div>

                        <div className="space-y-2">
                            {items.map((item) => {
                                const Icon = ICONS[item.node_type] ?? Bot;

                                return (
                                    <button
                                        key={item.node_type}
                                        onClick={() => addNode(item)}
                                        className="group w-full rounded-2xl border border-slate-200 bg-white p-3 text-left transition hover:border-slate-300 hover:bg-slate-50"
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700 group-hover:bg-slate-950 group-hover:text-white">
                                                <Icon size={17} />
                                            </div>

                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center justify-between gap-2">
                                                    <div className="truncate text-sm font-semibold text-slate-950">
                                                        {nodeLabel(item)}
                                                    </div>
                                                    <span className="text-slate-400">＋</span>
                                                </div>

                                                <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                                                    {nodeDescription(item)}
                                                </div>
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>
        </aside>
    );
}