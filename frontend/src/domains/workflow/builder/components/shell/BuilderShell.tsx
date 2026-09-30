"use client";

import type { ReactNode } from "react";

type BuilderShellProps = {
  palette: ReactNode;
  toolbar: ReactNode;
  canvas: ReactNode;
  inspector: ReactNode;
  runOutput: ReactNode;
  modals?: ReactNode;
};

export default function BuilderShell({
  palette,
  toolbar,
  canvas,
  inspector,
  runOutput,
  modals,
}: BuilderShellProps) {
  return (
    <div className="flex h-[calc(100vh-80px)] min-h-[720px] overflow-hidden rounded-3xl border border-slate-200 bg-slate-50">
      {palette}

      <main className="relative min-w-0 flex-1 bg-slate-100">
        <div className="absolute left-4 top-4 z-20">{toolbar}</div>
        <div className="h-full w-full">{canvas}</div>
      </main>

      <aside className="flex w-[380px] shrink-0 flex-col border-l border-slate-200 bg-white">
        <div className="min-h-0 flex-1 overflow-auto">{inspector}</div>
        <div className="max-h-[45%] overflow-auto border-t border-slate-200 bg-white">
          {runOutput}
        </div>
      </aside>

      {modals}
    </div>
  );
}
