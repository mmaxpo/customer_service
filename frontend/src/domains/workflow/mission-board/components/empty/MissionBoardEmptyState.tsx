"use client";

import Link from "next/link";

export function MissionBoardEmptyState() {
  return (
    <main className="flex min-h-[calc(100vh-80px)] items-center justify-center bg-slate-950 p-8">
      <div className="w-full max-w-3xl rounded-[36px] border border-slate-800 bg-slate-900 p-10 text-center shadow-2xl">
        <div className="text-sm font-extrabold uppercase tracking-[0.3em] text-tajeran-300">
          AI Operations Center
        </div>

        <h1 className="mt-4 text-4xl font-black tracking-tight text-white">
          No AI mission is currently running
        </h1>

        <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-slate-400">
          AI Operations Center becomes alive when an AI mission is executing.
          Open it from a customer conversation to observe a real mission,
          or load a workflow template to inspect its architecture.
        </p>

        <div className="mt-10 grid gap-4 md:grid-cols-2">
          <Link
            href="/app/inbox"
            className="rounded-3xl border border-emerald-700 bg-emerald-950 p-6 text-left transition hover:border-emerald-500"
          >
            <div className="text-lg font-black text-white">
              Observe a live mission
            </div>

            <div className="mt-3 text-sm leading-7 text-emerald-200">
              Open Inbox, find a conversation with an active workflow and
              click <strong>Observe Mission</strong>.
            </div>
          </Link>

          <Link
            href="/app/workflows"
            className="rounded-3xl border border-slate-700 bg-slate-950 p-6 text-left transition hover:border-slate-500"
          >
            <div className="text-lg font-black text-white">
              Explore a workflow
            </div>

            <div className="mt-3 text-sm leading-7 text-slate-300">
              Open the Workflow Builder and inspect any mission without
              running it.
            </div>
          </Link>
        </div>

        <div className="mt-10 rounded-3xl border border-slate-800 bg-black/20 p-6 text-left">
          <div className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
            Typical Flow
          </div>

          <div className="mt-4 text-sm leading-8 text-slate-300">
            Customer Message
            <br />
            ↓
            <br />
            Inbox
            <br />
            ↓
            <br />
            AI starts Mission
            <br />
            ↓
            <br />
            Observe Mission
            <br />
            ↓
            <br />
            AI Operations Center
            <br />
            ↓
            <br />
            Customer receives reply
          </div>
        </div>
      </div>
    </main>
  );
}
