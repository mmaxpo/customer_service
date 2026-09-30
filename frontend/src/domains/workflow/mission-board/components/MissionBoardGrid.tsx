"use client";

function Card({
  title,
  description,
  size = "normal",
}: {
  title: string;
  description: string;
  size?: "normal" | "large" | "wide";
}) {
  const className =
    size === "large"
      ? "md:col-span-2 md:row-span-2"
      : size === "wide"
        ? "md:col-span-2"
        : "";

  return (
    <section
      className={[
        "rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/70",
        className,
      ].join(" ")}
    >
      <div className="text-lg font-extrabold text-slate-950">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>

      <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm font-semibold text-slate-400">
        Coming next
      </div>
    </section>
  );
}

export default function MissionBoardGrid() {
  return (
    <div className="grid auto-rows-[220px] gap-4 md:grid-cols-4">
      <Card
        title="Mission Graph"
        description="A full-size map of agents, tools, decisions, approvals, and outputs."
        size="large"
      />

      <Card
        title="Runtime Timeline"
        description="Step-by-step execution events, agent activity, tool calls, pauses, and results."
        size="wide"
      />

      <Card
        title="Mission Health"
        description="Architecture score, missing paths, disconnected steps, and improvement warnings."
      />

      <Card
        title="Data Flow"
        description="What each step receives, creates, stores, and passes forward."
      />

      <Card
        title="Agent Control"
        description="Inspect every agent identity, responsibility, tools, memory, limits, and outputs."
      />

      <Card
        title="Approvals"
        description="See pending human decisions and control approved or rejected mission branches."
      />

      <Card
        title="State / Vars"
        description="Inspect runtime variables, outputs, tool results, and mission state."
      />

      <Card
        title="Architect Suggestions"
        description="Tajeran recommendations for improving mission quality and reliability."
      />
    </div>
  );
}
