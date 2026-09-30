"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, ArrowRight, Loader2, RefreshCw } from "lucide-react";

import { workflowApi } from "@/platform/api";

type RunItem = {
  workflow_run_id: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  thread_id?: string | null;
  answer?: string | null;
};

function formatDate(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusClass(status: string) {
  const normalized = status.toLowerCase();

  if (["completed", "success", "succeeded", "ok"].includes(normalized)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }

  if (["failed", "error"].includes(normalized)) {
    return "border-red-200 bg-red-50 text-red-700";
  }

  if (["paused", "waiting", "pending"].includes(normalized)) {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }

  return "border-slate-200 bg-slate-50 text-slate-600";
}

export default function RunsList() {
  const [items, setItems] = useState<RunItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "paused" | "completed" | "failed">("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredItems = useMemo(() => {
    if (statusFilter === "all") return items;

    return items.filter((item) => {
      const status = item.status.toLowerCase();

      if (statusFilter === "running") return ["running", "started"].includes(status);
      if (statusFilter === "paused") return ["paused", "waiting", "pending"].includes(status);
      if (statusFilter === "completed") return ["completed", "success", "succeeded", "ok"].includes(status);
      if (statusFilter === "failed") return ["failed", "error"].includes(status);

      return true;
    });
  }, [items, statusFilter]);

  async function load() {
    try {
      setLoading(true);
      setError(null);

      const data = await workflowApi.listRuns("limit=30&offset=0");
      setItems(data.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load workflow runs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load().catch(() => {});
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2 font-semibold text-slate-950">
            <Activity size={17} />
            Runtime history
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {loading ? "Loading runs..." : `${filteredItems.length} of ${items.length} runs shown`}
          </p>
        </div>

        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? <Loader2 className="animate-spin" size={15} /> : <RefreshCw size={15} />}
          Refresh
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          ["all", "All"],
          ["running", "Running"],
          ["paused", "Paused"],
          ["completed", "Completed"],
          ["failed", "Failed"],
        ].map(([value, label]) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value as typeof statusFilter)}
            className={[
              "rounded-full px-3 py-1 text-xs font-medium transition",
              statusFilter === value
                ? "bg-slate-950 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {filteredItems.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
          No workflow runs match this filter yet.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((run) => (
            <div
              key={run.workflow_run_id}
              className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={[
                        "rounded-full border px-2.5 py-1 text-xs font-medium capitalize",
                        statusClass(run.status),
                      ].join(" ")}
                    >
                      {run.status}
                    </span>

                    <span className="text-xs text-slate-500">
                      Updated {formatDate(run.updated_at)}
                    </span>
                  </div>

                  <div className="mt-3 truncate font-mono text-xs text-slate-500">
                    {run.workflow_run_id}
                  </div>

                  {run.answer && (
                    <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-600">
                      {String(run.answer)}
                    </p>
                  )}
                </div>

                <Link
                  href={`/app/runs/${run.workflow_run_id}`}
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  Open trace
                  <ArrowRight size={15} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
