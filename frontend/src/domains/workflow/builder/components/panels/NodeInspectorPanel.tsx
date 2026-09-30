import type { Node } from "@xyflow/react";
import type { CatalogItem } from "@/domains/workflow/builder/types/catalog";
import type { AgentToolCatalogItem } from "@/platform/api";
type Props = {
    selectedNode: Node | null;
    catalogByType: Map<string, CatalogItem>;
    updateSelectedNodeField: (key: string, value: any) => void;
    agentTools: AgentToolCatalogItem[];
    agentToolsStatus: string;
};

const NODE_TITLES: Record<string, string> = {
    "trigger.message": "Customer Message",
    "agent.custom": "AI Agent",
    "human.approval": "Human Approval",
    response: "Send Response",
    "router.rules": "Rules Router",
    "router.llm": "AI Router",
    "join.all": "Join Results",
    "set.variable": "Set Value",
    "kb.search": "Search Knowledge",
    "llm.generate": "Generate Text",
};

function FieldLabel({ children }: { children: React.ReactNode }) {
    return <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">{children}</label>;
}

function TextInput({
                       value,
                       onChange,
                       placeholder,
                   }: {
    value: any;
    onChange: (value: string) => void;
    placeholder?: string;
}) {
    return (
        <input
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
        />
    );
}

function TextArea({
                      value,
                      onChange,
                      placeholder,
                      minHeight = 96,
                  }: {
    value: any;
    onChange: (value: string) => void;
    placeholder?: string;
    minHeight?: number;
}) {
    return (
        <textarea
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            style={{ minHeight }}
            className="mt-2 w-full resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
        />
    );
}

export default function NodeInspectorPanel({
                                               selectedNode,
                                               catalogByType,
                                               updateSelectedNodeField,
                                               agentTools,
                                               agentToolsStatus,
                                           }: Props) {
    if (!selectedNode) {
        return (
            <aside className="p-4">
                <div className="font-semibold text-slate-950">Inspector</div>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                    Select a node to edit only the fields that matter. Technical runtime fields are auto-filled.
                </p>
            </aside>
        );
    }

    const data = selectedNode.data as any;
    const nodeType = String(data.nodeType ?? "");
    const item = catalogByType.get(nodeType);
    const title = NODE_TITLES[nodeType] ?? item?.title ?? nodeType;

    return (
        <aside className="p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="font-semibold text-slate-950">{title}</div>
                    <div className="mt-1 text-xs text-slate-500">{nodeType}</div>
                </div>

                <div className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                    Smart config
                </div>
            </div>

            <div className="mt-5 space-y-5">
                {nodeType === "tool.reference" && (
                    <>
                        <div>
                            <FieldLabel>Tool</FieldLabel>
                            <div className="mt-2 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                                <div className="text-sm font-semibold text-slate-950">
                                    {data.tool_title ?? data.name ?? "Tool"}
                                </div>
                                <p className="mt-1 text-xs leading-5 text-slate-500">
                                    {data.tool_description ?? "Agent capability tool."}
                                </p>
                            </div>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                            {data.connectedAgentName
                                ? `Connected to: ${data.connectedAgentName}`
                                : "Connect this tool into an AI Agent to make it available."}
                        </div>
                    </>
                )}
                {nodeType === "trigger.message" && (
                    <div>
                        <FieldLabel>Customer message</FieldLabel>
                        <TextArea
                            value={data.input}
                            onChange={(v) => updateSelectedNodeField("input", v)}
                            placeholder="Example: Refund order ORD-991 for 149"
                            minHeight={120}
                        />
                    </div>
                )}

                {nodeType === "agent.custom" && (
                    <>
                        <div>
                            <FieldLabel>Agent name</FieldLabel>
                            <TextInput
                                value={data.name ?? data.label}
                                onChange={(v) => {
                                    updateSelectedNodeField("name", v);
                                    updateSelectedNodeField("label", v);
                                }}
                                placeholder="Refund Agent"
                            />
                        </div>
                        <div>
                            <label>Role</label>

                            <select

                                value={data.role || "worker"}

                                onChange={(e) => updateSelectedNodeField("role", e.target.value)}

                            >

                                <option value="worker">Worker</option>

                                <option value="decision">Decision</option>

                                <option value="final">Final writer</option>

                            </select>
                        </div>

                        <div>
                            <FieldLabel>Responsibility</FieldLabel>
                            <TextArea
                                value={data.system_prompt}
                                onChange={(v) => updateSelectedNodeField("system_prompt", v)}
                                placeholder="Tell this agent what it is responsible for..."
                                minHeight={140}
                            />
                        </div>

                        <div>
                            <FieldLabel>Tools</FieldLabel>

                            <div className="mt-2 flex flex-wrap gap-2">
                                {agentTools.map((tool) => {
                                    const selected = Array.isArray(data.tools) && data.tools.includes(tool.name);

                                    return (
                                        <button
                                            key={tool.name}
                                            type="button"
                                            onClick={() => {
                                                const current = Array.isArray(data.tools) ? data.tools : [];

                                                const next = selected
                                                    ? current.filter((name: string) => name !== tool.name)
                                                    : [...current, tool.name];

                                                updateSelectedNodeField("tools", next);
                                            }}
                                            className={[
                                                "rounded-full border px-3 py-1.5 text-xs font-medium transition",
                                                selected
                                                    ? "border-slate-950 bg-slate-950 text-white"
                                                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
                                            ].join(" ")}
                                        >
                                            {tool.title}
                                        </button>
                                    );
                                })}
                            </div>

                            <p className="mt-2 text-xs leading-5 text-slate-500">
                                {agentToolsStatus || "Select tools this agent can use."}
                            </p>
                        </div>

                        <div>
                            <FieldLabel>Max steps</FieldLabel>
                            <TextInput
                                value={data.max_steps ?? 5}
                                onChange={(v) => updateSelectedNodeField("max_steps", Number(v || 5))}
                            />
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                            Auto-filled: backend, pattern, input source, input key, output key, retries, timeouts.
                        </div>
                    </>
                )}

                {nodeType === "human.approval" && (
                    <>
                        <div>
                            <FieldLabel>Approval question</FieldLabel>
                            <TextArea
                                value={data.question}
                                onChange={(v) => updateSelectedNodeField("question", v)}
                                placeholder="Approve this refund?"
                                minHeight={110}
                            />
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                            Auto-filled: input key, save key, approval field, retries, timeouts.
                        </div>
                    </>
                )}

                {nodeType === "response" && (
                    <>
                        <div>
                            <FieldLabel>Response name</FieldLabel>
                            <TextInput
                                value={data.name ?? data.label}
                                onChange={(v) => {
                                    updateSelectedNodeField("name", v);
                                    updateSelectedNodeField("label", v);
                                }}
                                placeholder="Final Response"
                            />
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                            This response automatically returns output from:{" "}
                            <span className="font-semibold text-slate-900">
                                {data.answer_key ?? "previous node"}
                            </span>
                        </div>
                    </>
                )}

                {!["trigger.message", "agent.custom", "human.approval", "response", "tool.reference"].includes(nodeType) && (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                        This node is currently using smart defaults. Advanced editing will be added after the core workflow UX is stable.
                    </div>
                )}
            </div>
        </aside>
    );
}