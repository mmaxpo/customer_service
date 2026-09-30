"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";
import { ConfirmDialog } from "@/ui/overlay/ConfirmDialog";

import { formatDay, formatTime } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import { studioApi, type VersionHistory, type WorkflowVersion } from "./api";

function statusChip(version: WorkflowVersion, live: number | null) {
  if (version.version === live) return <ToneChip tone="commerce">Live</ToneChip>;
  if (version.status === "draft") return <ToneChip tone="attention">Draft</ToneChip>;
  return <ToneChip tone="neutral">Earlier version</ToneChip>;
}

export default function VersionHistoryScreen({ workflowId }: { workflowId: string }) {
  const [history, setHistory] = useState<VersionHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<WorkflowVersion | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () =>
    studioApi.versions(workflowId).then(setHistory).catch((err) => setError(apiErrorMessage(err, "Could not load version history.")));

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId]);

  const restore = async () => {
    if (!restoring) return;
    setBusy(true);
    setError(null);
    try {
      await studioApi.restoreVersion(workflowId, restoring.version);
      setRestoring(null);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not restore this version."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <nav aria-label="Breadcrumb" className="mb-3 flex flex-wrap items-center gap-1.5 text-[13.5px]">
        <Link href="/app/workflows" className="text-text-secondary hover:text-foreground">Workflows</Link>
        <span className="text-text-secondary">/</span>
        <span className="text-text-secondary">{history?.workflow_name ?? "Workflow"}</span>
      </nav>
      <header className="mb-5">
        <h1 className="text-[18px] font-semibold text-foreground">Version history</h1>
        <p className="mt-0.5 text-[13.5px] text-text-secondary">
          Every published change is kept. Restoring an earlier version makes it live again for new messages.
        </p>
      </header>

      {error ? <p role="alert" className="mb-3 text-[13.5px] text-danger">{error}</p> : null}
      {!history && !error ? (
        <p className="flex items-center gap-2 text-[13.5px] text-text-secondary">
          <Loader2 size={15} className="animate-spin" aria-hidden /> Loading…
        </p>
      ) : null}
      {history && !history.versions.length ? (
        <p className="rounded-container border border-border bg-surface p-6 text-center text-[13.5px] text-text-secondary">
          No changes have been published yet. The first change you make starts the history.
        </p>
      ) : null}

      {history?.versions.length ? (
        <ol className="divide-y divide-border overflow-hidden rounded-container border border-border bg-surface">
          {history.versions.map((version) => {
            const canRestore = version.version !== history.live_version && version.status !== "draft";
            return (
              <li key={version.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-[14.5px] font-semibold text-foreground">v{version.version}</h2>
                    {statusChip(version, history.live_version)}
                    <span className="text-[12px] tabular-nums text-text-secondary">
                      {formatDay(version.published_at ?? version.created_at)} at {formatTime(version.published_at ?? version.created_at)}
                    </span>
                  </div>
                  <p className="mt-1 text-[13px] text-foreground">
                    {version.kind === "import" ? "Starting point: the workflow as it was running." : version.note}
                  </p>
                  {version.summary.filter((line) => line.kind !== "same").length ? (
                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-[12.5px] text-text-secondary">
                      {version.summary.filter((line) => line.kind !== "same").map((line, index) => <li key={index}>{line.text}</li>)}
                    </ul>
                  ) : null}
                  {version.status === "draft" ? (
                    <Link href={`/app/workflows/proposals/${version.id}`} className="mt-1 inline-block text-[12.5px] font-medium text-primary hover:underline">
                      Review this draft
                    </Link>
                  ) : null}
                </div>
                {canRestore ? (
                  <Button variant="secondary" size="sm" className="shrink-0" onClick={() => setRestoring(version)}>
                    Restore v{version.version}
                  </Button>
                ) : null}
              </li>
            );
          })}
        </ol>
      ) : null}

      <ConfirmDialog
        open={restoring !== null}
        onOpenChange={(open) => !open && setRestoring(null)}
        title={`Restore v${restoring?.version ?? ""}?`}
        description={
          <p>
            New customer messages for {history?.workflow_name} will use v{restoring?.version} right away. v{history?.live_version} stays in the history, so you can switch back.
          </p>
        }
        confirmLabel={`Restore v${restoring?.version ?? ""}`}
        busy={busy}
        onConfirm={() => void restore()}
      />
    </div>
  );
}
