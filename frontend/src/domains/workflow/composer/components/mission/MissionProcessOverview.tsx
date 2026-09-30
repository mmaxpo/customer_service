"use client";

import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

type Props = {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
};

function categoryLabel(value?: string) {
  const map: Record<string, string> = {
    trigger: "Start",
    agent: "Agent",
    action: "Tool",
    approval: "Human Decision",
    decision: "Decision",
    knowledge: "Knowledge",
    response: "Output",
    group: "Parallel Work",
  };

  return map[value || ""] || "Step";
}

function buildOrderedNodes(nodes: ComposerNodeType[], edges: ComposerEdge[]) {
  if (nodes.length <= 1) return nodes;

  const targetIds = new Set(edges.map((edge) => edge.target));
  const start = nodes.find((node) => !targetIds.has(node.id)) || nodes[0];
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const outgoing = new Map<string, string[]>();

  for (const edge of edges) {
    outgoing.set(edge.source, [...(outgoing.get(edge.source) || []), edge.target]);
  }

  const ordered: ComposerNodeType[] = [];
  const seen = new Set<string>();
  const queue = [start.id];

  while (queue.length) {
    const id = queue.shift()!;
    if (seen.has(id)) continue;

    const node = byId.get(id);
    if (!node) continue;

    seen.add(id);
    ordered.push(node);

    for (const next of outgoing.get(id) || []) {
      if (!seen.has(next)) queue.push(next);
    }
  }

  for (const node of nodes) {
    if (!seen.has(node.id)) ordered.push(node);
  }

  return ordered;
}

export default function MissionProcessOverview({ nodes, edges }: Props) {
  const orderedNodes = buildOrderedNodes(nodes, edges);

  return (
    <section className="mb-4 overflow-hidden rounded-3xl border border-tajeran-100 bg-white shadow-sm shadow-tajeran-100/70">
      <div className="bg-gradient-to-br from-tajeran-950 to-ai-950 p-4 text-white">
        <div className="text-xs font-bold uppercase tracking-wide text-tajeran-100">
          Mission Process
        </div>
        <div className="mt-1 text-lg font-extrabold tracking-tight">
          Visual execution path
        </div>
        <div className="mt-2 text-xs leading-5 text-tajeran-100">
          {nodes.length} mission step(s), {edges.length} path(s)
        </div>
      </div>

      <div className="space-y-3 p-4">
        {orderedNodes.length === 0 ? (
          <div className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-500">
            Add agents, tools, decisions, and outputs to see the mission process.
          </div>
        ) : (
          orderedNodes.map((node, index) => (
            <div key={node.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-tajeran-950 text-xs font-extrabold text-white">
                  {index + 1}
                </div>
                {index < orderedNodes.length - 1 && (
                  <div className="mt-1 h-8 w-px bg-slate-200" />
                )}
              </div>

              <div className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate text-sm font-extrabold text-slate-950">
                    {node.data.label}
                  </div>
                  <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-slate-500">
                    {categoryLabel(node.data.category)}
                  </span>
                </div>

                <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                  {node.data.config?.responsibility ||
                    node.data.description ||
                    "Mission step"}
                </div>

                <div className="mt-2 flex flex-wrap gap-1">
                  {node.data.businessInputs?.slice(0, 2).map((item) => (
                    <span
                      key={`in-${node.id}-${item}`}
                      className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-600"
                    >
                      Understands {item}
                    </span>
                  ))}

                  {node.data.businessOutputs?.slice(0, 2).map((item) => (
                    <span
                      key={`out-${node.id}-${item}`}
                      className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700"
                    >
                      Creates {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
