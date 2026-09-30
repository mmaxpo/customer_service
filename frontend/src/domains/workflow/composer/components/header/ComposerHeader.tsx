"use client";

import type { WorkflowTemplate } from "@/domains/customer-service/api/customer-service";

type Props = {
  nodesCount: number;
  edgesCount: number;
  loadedTemplate: WorkflowTemplate | null;
  templateSlug: string | null;

  hasSelectedNode: boolean;
  hasSelectedEdge: boolean;

  addStarterFlow: () => void;
  saveDraft: () => void;
  duplicateSelectedNode: () => void;
  deleteSelectedNode: () => void;
  deleteSelectedEdge: () => void;
  autoLayout: () => void;
  fitView: () => void;
  runCompiledWorkflow: () => void;

  saveStatus: string;
  runStatus: string;
};

export default function ComposerHeader({
  nodesCount,
  edgesCount,
  loadedTemplate,
  templateSlug,
  hasSelectedNode,
  hasSelectedEdge,
  addStarterFlow,
  saveDraft,
  duplicateSelectedNode,
  deleteSelectedNode,
  deleteSelectedEdge,
  autoLayout,
  fitView,
  runCompiledWorkflow,
  saveStatus,
  runStatus,
}: Props) {
  return (
    <div className="flex h-20 items-center justify-between border-b border-tajeran-100 bg-white/90 px-5 shadow-sm shadow-tajeran-100/60 backdrop-blur">
      <div>
        <div className="text-lg font-extrabold tracking-tight text-slate-950">
          Support automation
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-tajeran-50 px-2.5 py-1 font-semibold text-tajeran-700">
            {nodesCount} steps
          </span>
          <span className="rounded-full bg-ai-50 px-2.5 py-1 font-semibold text-ai-700">
            {edgesCount} connections
          </span>
          <span className="text-slate-500">
            {loadedTemplate?.name || templateSlug?.replaceAll("-", " ") || "Turn repeat questions into safe, helpful replies"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {nodesCount === 0 && (
          <button
            onClick={addStarterFlow}
            className="rounded-2xl border border-tajeran-100 bg-white px-3 py-2 text-xs font-bold text-tajeran-700 shadow-sm hover:bg-tajeran-50"
          >
            Start with order support
          </button>
        )}

        {loadedTemplate && (
          <button
            onClick={saveDraft}
            disabled={loadedTemplate.scope !== "private" || loadedTemplate.status !== "draft"}
            className="rounded-2xl border border-tajeran-100 bg-white px-3 py-2 text-xs font-bold text-tajeran-700 shadow-sm hover:bg-tajeran-50 disabled:opacity-50"
          >
            Save draft
          </button>
        )}

        {hasSelectedNode && (
          <button
            onClick={duplicateSelectedNode}
            className="rounded-2xl border border-tajeran-100 bg-white px-3 py-2 text-xs font-bold text-tajeran-700 hover:bg-tajeran-50"
          >
            Duplicate step
          </button>
        )}

        {hasSelectedNode && (
          <button
            onClick={deleteSelectedNode}
            className="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-100"
          >
            Delete step
          </button>
        )}

        {hasSelectedEdge && (
          <button
            onClick={deleteSelectedEdge}
            className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700 hover:bg-amber-100"
          >
            Delete path
          </button>
        )}

        <button
          onClick={autoLayout}
          disabled={nodesCount === 0}
          className="rounded-2xl border border-ai-100 bg-ai-50 px-3 py-2 text-xs font-bold text-ai-700 shadow-sm hover:bg-ai-100 disabled:opacity-50"
        >
          Arrange steps
        </button>

        <button
          onClick={fitView}
          disabled={nodesCount === 0}
          className="rounded-2xl border border-tajeran-100 bg-white px-3 py-2 text-xs font-bold text-tajeran-700 shadow-sm hover:bg-tajeran-50 disabled:opacity-50"
        >
          Center workflow
        </button>

        <button
          onClick={runCompiledWorkflow}
          disabled={nodesCount === 0}
          className="rounded-2xl bg-gradient-to-r from-tajeran-950 to-ai-950 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-tajeran-950/20 disabled:opacity-50"
        >
          Test workflow
        </button>

        <a
          href="/app/workflows/mission-board"
          className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs font-extrabold text-slate-700 shadow-sm hover:bg-slate-50"
        >
          Run history →
        </a>

        {(saveStatus || runStatus) && (
          <div className="max-w-56 truncate rounded-2xl bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600">
            {saveStatus || runStatus}
          </div>
        )}
      </div>
    </div>
  );
}
