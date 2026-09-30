"use client";

import type { ReactNode } from "react";

type Props = {
  palette: ReactNode;
  header: ReactNode;
  canvas: ReactNode;
  sidePanel: ReactNode;
};

export default function ComposerShell({
  palette,
  header,
  canvas,
  sidePanel,
}: Props) {
  return (
    <div className="flex h-[calc(100vh-120px)] overflow-hidden rounded-[32px] border border-tajeran-100 bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.10),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.10),transparent_28%),#f8fafc] shadow-xl shadow-tajeran-100/50">
      {palette}

      <main className="min-w-0 flex-1 overflow-hidden">
        {header}
        <div className="h-full overflow-hidden rounded-[28px]">
          {canvas}
        </div>
      </main>

      <div className="flex">{sidePanel}</div>
    </div>
  );
}
