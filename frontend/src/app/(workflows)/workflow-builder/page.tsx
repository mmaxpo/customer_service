// src/app/(workflows)/workflow-builder/page.tsx
"use client";

import Link from "next/link";
import WorkflowBuilder from "@/domains/workflow/builder/components/WorkflowBuilder";

export default function WorkflowBuilderPage() {
    return (
        <div className="flex min-h-screen flex-col bg-slate-50">
        <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4">
        <div>
            <div className="text-sm font-semibold text-slate-950">
            Tajeran.ai Workflow Builder
    </div>
    <div className="text-xs text-slate-500">
        Internal advanced runtime builder
    </div>
    </div>

    <nav className="flex items-center gap-2 text-sm">
    <Link
        href="/app/dashboard"
    className="rounded-xl border border-slate-200 px-3 py-2 hover:bg-slate-50"
        >
        Dashboard
        </Link>
        <Link
    href="/app/workflows"
    className="rounded-xl border border-slate-200 px-3 py-2 hover:bg-slate-50"
        >
        Workflows
        </Link>
        <Link
    href="/runs"
    className="rounded-xl border border-slate-200 px-3 py-2 hover:bg-slate-50"
        >
        Runs
        </Link>
        <Link
    href="/dev-console"
    className="rounded-xl bg-slate-950 px-3 py-2 text-white hover:bg-slate-800"
        >
        Admin
        </Link>
        </nav>
        </header>

        <WorkflowBuilder />
        </div>
);
}