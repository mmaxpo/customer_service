"use client";

import type { ComposerNode as ComposerNodeType } from "@/domains/workflow/composer/types/composer";

type Props = {
  selectedNode: ComposerNodeType | null;
  updateNodeLabel: (nodeId: string, label: string) => void;
  updateNodeConfig: (nodeId: string, patch: Record<string, unknown>) => void;
};

function categoryTitle(category?: string) {
  const map: Record<string, string> = {
    trigger: "Mission Start",
    agent: "AI Agent",
    action: "Tool Capability",
    approval: "Human Decision",
    decision: "Decision Logic",
    knowledge: "Knowledge Source",
    response: "Mission Output",
    group: "Parallel Agent Group",
  };

  return map[category || ""] || "Mission Step";
}

export default function MissionStepInspector({
  selectedNode,
  updateNodeLabel,
  updateNodeConfig,
}: Props) {
  if (!selectedNode) {
    return (
      <section className="mb-4 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/70">
        <div className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
          Agent Identity
        </div>
        <div className="mt-1 text-lg font-extrabold text-slate-950">
          Select a mission step
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Select an agent, tool, decision, or output to define its identity, responsibility, capabilities, and success.
        </p>
      </section>
    );
  }

  const data = selectedNode.data;
  const config = data.config || {};

  return (
    <section className="mb-4 overflow-hidden rounded-3xl border border-ai-100 bg-white shadow-sm shadow-ai-100/70">
      <div className="bg-gradient-to-br from-ai-700 to-tajeran-950 p-4 text-white">
        <div className="text-xs font-bold uppercase tracking-wide text-ai-100">
          Agent Identity
        </div>

        <input
          value={data.label}
          onChange={(event) => updateNodeLabel(selectedNode.id, event.target.value)}
          className="mt-2 w-full rounded-2xl border border-white/20 bg-white/10 px-3 py-2 text-sm font-bold text-white outline-none placeholder:text-white/60"
          placeholder="Mission step name"
        />

        <div className="mt-2 inline-flex rounded-full bg-white/10 px-2.5 py-1 text-xs font-bold text-ai-100">
          {categoryTitle(data.category)}
        </div>
      </div>

      <div className="space-y-4 p-4 text-sm">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
            Identity
          </div>
          <div className="mt-1 text-sm font-bold text-slate-950">
            {categoryTitle(data.category)}
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            {data.description || "This step participates in the mission."}
          </p>
        </div>

        {data.blockKind === "customer_message_trigger" && (
          <label className="block rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
              Mission input
            </div>
            <textarea
              value={config.input ?? ""}
              onChange={(event) =>
                updateNodeConfig(selectedNode.id, { input: event.target.value })
              }
              className="mt-2 min-h-24 w-full resize-none rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-tajeran-200 focus:ring-2 focus:ring-tajeran-100"
              placeholder="Example: Where is my order #1001?"
            />
          </label>
        )}

        {data.category === "agent" && (
          <label className="block rounded-2xl border border-ai-100 bg-ai-50/50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-ai-700">
              Responsibility
            </div>
            <textarea
              value={config.responsibility ?? ""}
              onChange={(event) =>
                updateNodeConfig(selectedNode.id, { responsibility: event.target.value })
              }
              className="mt-2 min-h-32 w-full resize-none rounded-2xl border border-ai-100 bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-ai-200 focus:ring-2 focus:ring-ai-100"
              placeholder="Define what this agent must understand, decide, verify, or create."
            />
          </label>
        )}

        {data.blockKind === "human_approval" && (
          <label className="block rounded-2xl border border-amber-100 bg-amber-50/50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-amber-700">
              Human decision checkpoint
            </div>
            <textarea
              value={config.question ?? ""}
              onChange={(event) =>
                updateNodeConfig(selectedNode.id, { question: event.target.value })
              }
              className="mt-2 min-h-24 w-full resize-none rounded-2xl border border-amber-100 bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-amber-200 focus:ring-2 focus:ring-amber-100"
              placeholder="Example: Should a manager approve this refund?"
            />
          </label>
        )}

        {data.blockKind === "business_router" && (
          <label className="block rounded-2xl border border-purple-100 bg-purple-50/50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-purple-700">
              Decision signal
            </div>
            <input
              value={config.key ?? ""}
              onChange={(event) =>
                updateNodeConfig(selectedNode.id, { key: event.target.value })
              }
              className="mt-2 w-full rounded-2xl border border-purple-100 bg-white px-3 py-2 text-sm outline-none focus:border-purple-200 focus:ring-2 focus:ring-purple-100"
              placeholder="intent"
            />
          </label>
        )}

        {data.blockKind === "knowledge_answer" && (
          <label className="block rounded-2xl border border-shopify-100 bg-shopify-50/50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-shopify-700">
              Knowledge depth
            </div>
            <input
              type="number"
              min={1}
              max={20}
              value={config.top_k ?? 5}
              onChange={(event) =>
                updateNodeConfig(selectedNode.id, { top_k: Number(event.target.value) })
              }
              className="mt-2 w-full rounded-2xl border border-shopify-100 bg-white px-3 py-2 text-sm outline-none focus:border-shopify-200 focus:ring-2 focus:ring-shopify-100"
            />
          </label>
        )}

        {data.blockKind === "send_response" && (
          <label className="block rounded-2xl border border-emerald-100 bg-emerald-50/50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-emerald-700">
              Success / final output source
            </div>
            <input
              value={config.answer_key ?? ""}
              onChange={(event) =>
                updateNodeConfig(selectedNode.id, { answer_key: event.target.value })
              }
              className="mt-2 w-full rounded-2xl border border-emerald-100 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-200 focus:ring-2 focus:ring-emerald-100"
              placeholder="agent_result"
            />
          </label>
        )}

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-2xl bg-slate-50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
              Understands
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {(data.businessInputs || ["Mission context"]).map((item) => (
                <span
                  key={item}
                  className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-600"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-2xl bg-emerald-50 p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-emerald-700">
              Creates
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {(data.businessOutputs || ["Mission result"]).map((item) => (
                <span
                  key={item}
                  className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-emerald-700"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
