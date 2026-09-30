"use client";

import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

type Props = {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
};

function nodeLabel(nodes: ComposerNodeType[], id: string) {
  return nodes.find((node) => node.id === id)?.data.label || "Unknown step";
}

export default function MissionDataFlow({ nodes, edges }: Props) {
  return (
    <section className="mb-4 overflow-hidden rounded-3xl border border-emerald-100 bg-white shadow-sm shadow-emerald-100/70">
      <div className="bg-gradient-to-br from-emerald-600 to-tajeran-950 p-4 text-white">
        <div className="text-xs font-bold uppercase tracking-wide text-emerald-100">
          Mission Data Flow
        </div>
        <div className="mt-1 text-lg font-extrabold tracking-tight">
          What moves between agents
        </div>
        <div className="mt-2 text-xs leading-5 text-emerald-100">
          See what each step understands, creates, and passes forward.
        </div>
      </div>

      <div className="space-y-3 p-4">
        {nodes.length === 0 ? (
          <div className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-500">
            Add mission steps to see data flow.
          </div>
        ) : (
          nodes.map((node) => (
            <div
              key={node.id}
              className="rounded-2xl border border-slate-200 bg-slate-50 p-3"
            >
              <div className="text-sm font-extrabold text-slate-950">
                {node.data.label}
              </div>

              <div className="mt-2 grid grid-cols-2 gap-2">
                <div className="rounded-2xl bg-white p-2">
                  <div className="text-[10px] font-extrabold uppercase tracking-wide text-slate-400">
                    Understands
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {(node.data.businessInputs || ["Mission context"]).map((item) => (
                      <span
                        key={`${node.id}-in-${item}`}
                        className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl bg-emerald-50 p-2">
                  <div className="text-[10px] font-extrabold uppercase tracking-wide text-emerald-700">
                    Creates
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {(node.data.businessOutputs || ["Mission result"]).map((item) => (
                      <span
                        key={`${node.id}-out-${item}`}
                        className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-emerald-700"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}

        {edges.length > 0 && (
          <div className="rounded-2xl border border-slate-200 bg-white p-3">
            <div className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
              Mission paths
            </div>

            <div className="mt-2 space-y-2">
              {edges.slice(0, 6).map((edge) => (
                <div
                  key={edge.id}
                  className="rounded-2xl bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600"
                >
                  {nodeLabel(nodes, edge.source)} → {nodeLabel(nodes, edge.target)}
                </div>
              ))}
            </div>

            {edges.length > 6 && (
              <div className="mt-2 text-xs font-semibold text-slate-400">
                +{edges.length - 6} more path(s)
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
