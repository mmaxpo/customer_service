"use client";

import { useEffect, useState } from "react";

import { customerServiceApi, type WorkflowTemplate } from "@/domains/customer-service/api/customer-service";

function healthForTemplate(template: WorkflowTemplate) {
  if (template.status === "published") return 96;
  if (template.status === "draft") return 78;
  return 64;
}

export default function MissionBoardLauncher() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;

    async function loadTemplates() {
      setLoading(true);
      setError("");

      try {
        const data = await customerServiceApi.workflowTemplates();
        if (!alive) return;
        setTemplates(data);
      } catch (err) {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Failed to load missions");
      } finally {
        if (alive) setLoading(false);
      }
    }

    void loadTemplates();

    return () => {
      alive = false;
    };
  }, []);

  return (
    <main className="min-h-[calc(100vh-80px)] bg-slate-950 p-6">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-[36px] border border-slate-800 bg-slate-900 p-8 shadow-2xl shadow-black/30">
          <div className="text-xs font-extrabold uppercase tracking-[0.25em] text-tajeran-300">
            Mission Control
          </div>

          <h1 className="mt-3 text-4xl font-black tracking-tight text-white">
            Choose an AI mission to understand and operate
          </h1>

          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-400">
            The builder is where missions are designed. The AI Operations Center is where they become understandable:
            architecture, runtime proof, variables, agents, tools, snapshots, replay, and improvement paths.
          </p>

          {loading && (
            <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-950 p-5 text-sm font-semibold text-slate-400">
              Loading missions...
            </div>
          )}

          {error && (
            <div className="mt-8 rounded-3xl border border-red-900 bg-red-950/40 p-5 text-sm font-semibold text-red-200">
              {error}
            </div>
          )}

          {!loading && !error && templates.length === 0 && (
            <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-950 p-5">
              <div className="text-lg font-extrabold text-white">
                No missions found yet
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Create or seed workflow templates first, then return to AI Operations Center.
              </p>
            </div>
          )}

          {!loading && !error && templates.length > 0 && (
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {templates.map((template) => {
                const health = healthForTemplate(template);

                return (
                  <a
                    key={template.id}
                    href={`/app/workflows/mission-board?templateId=${template.id}`}
                    className="group rounded-[28px] border border-slate-800 bg-slate-950 p-5 transition hover:-translate-y-0.5 hover:border-tajeran-300 hover:shadow-xl hover:shadow-tajeran-950/30"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-xl font-extrabold text-white">
                          {template.name}
                        </div>
                        <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-500">
                          {template.description || "Open this mission to inspect architecture, runtime proof, agents, tools, and execution history."}
                        </p>
                      </div>

                      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white text-lg font-black text-slate-950">
                        {health}
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <span className="rounded-full bg-slate-900 px-2 py-1 text-[10px] font-extrabold uppercase text-slate-400">
                        {template.status}
                      </span>
                      <span className="rounded-full bg-slate-900 px-2 py-1 text-[10px] font-extrabold uppercase text-slate-400">
                        {template.scope}
                      </span>
                    </div>

                    <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-extrabold text-slate-400 transition group-hover:text-white">
                      Open mission board →
                    </div>
                  </a>
                );
              })}
            </div>
          )}

          <div className="mt-6 flex gap-3">
            <a
              href="/app/workflows/builder"
              className="rounded-2xl bg-white px-4 py-2 text-xs font-extrabold text-slate-950 hover:bg-slate-100"
            >
              Open Builder
            </a>

            <a
              href="/app/workflows"
              className="rounded-2xl border border-slate-700 px-4 py-2 text-xs font-extrabold text-slate-300 hover:bg-slate-800 hover:text-white"
            >
              Back to Workflows
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
