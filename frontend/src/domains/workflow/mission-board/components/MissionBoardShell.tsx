"use client";

type Props = {
  children?: React.ReactNode;
};

export default function MissionBoardShell({ children }: Props) {
  return (
    <main className="min-h-[calc(100vh-80px)] bg-slate-50 p-6">
      <div className="mx-auto max-w-[1600px]">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-700">
              AI Operations Center
            </div>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950">
              Observe, understand and operate every AI mission
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
              The builder creates the mission. The board lets you inspect the graph, understand execution,
              control approvals, debug state, review data flow, and improve the architecture.
            </p>
          </div>

          <div className="rounded-3xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-right">
            <div className="text-xs font-extrabold uppercase tracking-wide text-emerald-700">
              Board mode
            </div>
            <div className="mt-1 text-sm font-extrabold text-emerald-950">
              Analysis + Control
            </div>
          </div>
        </div>

        {children}
      </div>
    </main>
  );
}
