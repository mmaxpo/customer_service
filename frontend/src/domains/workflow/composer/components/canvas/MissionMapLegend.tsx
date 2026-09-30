"use client";

const ITEMS = [
  { label: "Start", dot: "bg-tajeran-600", meaning: "Mission begins" },
  { label: "Agent", dot: "bg-ai-600", meaning: "AI worker" },
  { label: "Tool", dot: "bg-shopify-600", meaning: "System action" },
  { label: "Decision", dot: "bg-purple-600", meaning: "Route / choose" },
  { label: "Human", dot: "bg-amber-500", meaning: "Approval checkpoint" },
  { label: "Output", dot: "bg-emerald-600", meaning: "Final result" },
];

export default function MissionMapLegend() {
  return (
    <div className="pointer-events-none absolute bottom-5 left-5 z-10 rounded-3xl border border-white/80 bg-white/90 p-3 shadow-xl shadow-slate-200/70 backdrop-blur">
      <div className="mb-2 text-[10px] font-extrabold uppercase tracking-wide text-slate-400">
        Mission language
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        {ITEMS.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <span className={["h-2.5 w-2.5 rounded-full", item.dot].join(" ")} />
            <div>
              <div className="text-[11px] font-extrabold text-slate-800">
                {item.label}
              </div>
              <div className="text-[9px] font-medium text-slate-400">
                {item.meaning}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
