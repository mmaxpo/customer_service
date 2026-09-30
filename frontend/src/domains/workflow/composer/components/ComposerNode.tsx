"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Bot, BookOpen, GitBranch, MessageCircle, PackageSearch, Send, ShieldCheck, Split } from "lucide-react";
import type { ComposerBlockInstanceData } from "../types/composer";

const icons: Record<string, any> = {
  trigger: MessageCircle,
  agent: Bot,
  group: GitBranch,
  approval: ShieldCheck,
  decision: Split,
  knowledge: BookOpen,
  response: Send,
  action: PackageSearch,
};

const styles: Record<string, { glow: string; icon: string; accent: string; ring: string }> = {
  trigger: { glow: "shadow-tajeran-200/70", icon: "bg-tajeran-50 text-tajeran-700", accent: "from-tajeran-500 to-tajeran-700", ring: "border-tajeran-200" },
  agent: { glow: "shadow-ai-200/70", icon: "bg-ai-50 text-ai-700", accent: "from-ai-500 to-ai-700", ring: "border-ai-200" },
  group: { glow: "shadow-slate-200/80", icon: "bg-slate-100 text-slate-700", accent: "from-slate-400 to-slate-700", ring: "border-slate-200" },
  approval: { glow: "shadow-amber-200/80", icon: "bg-amber-50 text-amber-700", accent: "from-amber-400 to-orange-600", ring: "border-amber-200" },
  decision: { glow: "shadow-purple-200/80", icon: "bg-purple-50 text-purple-700", accent: "from-purple-400 to-fuchsia-600", ring: "border-purple-200" },
  knowledge: { glow: "shadow-shopify-200/80", icon: "bg-shopify-50 text-shopify-700", accent: "from-shopify-500 to-emerald-600", ring: "border-shopify-200" },
  response: { glow: "shadow-emerald-200/80", icon: "bg-emerald-50 text-emerald-700", accent: "from-emerald-400 to-green-700", ring: "border-emerald-200" },
  action: { glow: "shadow-shopify-200/80", icon: "bg-shopify-50 text-shopify-700", accent: "from-shopify-500 to-emerald-600", ring: "border-shopify-200" },
};

export default function ComposerNode(props: NodeProps) {
  const data = props.data as ComposerBlockInstanceData;
  const Icon = icons[data.category] ?? Bot;
  const style = styles[data.category] ?? styles.agent;
  const summary = String(data.config?.responsibility || data.description || "");
  const runStatus = String((data as any).runStatus || "");

  const runtimeRing =
    runStatus === "running"
      ? "ring-4 ring-ai-300"
      : runStatus === "done"
        ? "ring-4 ring-emerald-300"
        : runStatus === "failed"
          ? "ring-4 ring-red-300"
          : runStatus === "paused"
            ? "ring-4 ring-amber-300"
            : "";

  return (
    <div className={["group relative w-44 rounded-2xl p-[1px] shadow-lg transition duration-300 hover:-translate-y-1 hover:shadow-2xl", style.glow, runtimeRing].join(" ")}>
      <div className={["absolute inset-0 rounded-2xl bg-gradient-to-br opacity-80 transition duration-300 group-hover:opacity-100", style.accent].join(" ")} />

      {data.category !== "trigger" && (
        <Handle
          className="!h-2.5 !w-2.5 !border-2 !border-white !bg-tajeran-700 !shadow-md"
          type="target"
          position={Position.Left}
        />
      )}

      <div className="relative overflow-hidden rounded-2xl border border-white/70 bg-white/95 backdrop-blur">
        <div className={["h-1 bg-gradient-to-r", style.accent].join(" ")} />

        <div className="p-2.5">
          <div className="flex items-center gap-2">
            <div className={["flex h-8 w-8 shrink-0 items-center justify-center rounded-xl shadow-sm ring-1 ring-white/80", style.icon].join(" ")}>
              <Icon size={14} />
            </div>

            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-extrabold tracking-tight text-slate-950">
                {data.label}
              </div>
              <div className="mt-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-400">
                {data.category}
              </div>
            </div>
          </div>

          <div className="mt-2">
            <p className="line-clamp-2 text-[10px] leading-4 text-slate-600">
              {summary}
            </p>

            {(data.businessInputs?.length || data.businessOutputs?.length) ? (
              <div className="mt-2 space-y-1.5">
                {data.businessInputs?.length ? (
                  <div>
                    <div className="mb-1 text-[8px] font-bold uppercase tracking-wider text-slate-400">
                      Understands
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {data.businessInputs.slice(0, 2).map((item) => (
                        <span
                          key={item}
                          className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[8px] font-semibold text-slate-600"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {data.businessOutputs?.length ? (
                  <div>
                    <div className="mb-1 text-[8px] font-bold uppercase tracking-wider text-slate-400">
                      Creates
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {data.businessOutputs.slice(0, 2).map((item) => (
                        <span
                          key={item}
                          className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[8px] font-semibold text-emerald-700"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/80 px-2.5 py-1">
          <span className="text-[9px] font-bold text-slate-400">Mission Step</span>
          {runStatus ? (
            <span className="rounded-full bg-white px-2 py-0.5 text-[9px] font-extrabold uppercase text-slate-600">
              {runStatus}
            </span>
          ) : (
            <span className={["h-1.5 w-1.5 rounded-full bg-gradient-to-r", style.accent].join(" ")} />
          )}
        </div>
      </div>

      {data.category !== "response" && (
        <Handle
          className="!h-2.5 !w-2.5 !border-2 !border-white !bg-ai-700 !shadow-md"
          type="source"
          position={Position.Right}
        />
      )}
    </div>
  );
}
