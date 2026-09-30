"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";

import { ApiError, apiErrorMessage } from "@/platform/api/client";
import { Events, usePublish } from "@/platform/events";
import { cn } from "@/platform/utils";
import { Button } from "@/ui/primitives/button";

import { useWorkflowLauncher } from "../features/workflow-launcher/hooks";

type Props = {
  conversationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function RunWorkflowDialog({ conversationId, open, onOpenChange }: Props) {
  const launcher = useWorkflowLauncher();
  const publish = usePublish();
  const [selected, setSelected] = useState("");
  const [request, setRequest] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (!selected || !request.trim()) return;
    setRunning(true);
    setError(null);
    try {
      await launcher.run(conversationId, selected, request.trim());
      publish({ type: Events.WorkflowStarted, payload: { conversationId, templateId: selected } });
      publish({ type: Events.RuntimeUpdated, payload: { conversationId } });
      publish({ type: Events.ConversationChanged, payload: { conversationId } });
      onOpenChange(false);
      setSelected("");
      setRequest("");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429
        ? "Tajeran is handling another request. Wait a moment and try again."
        : apiErrorMessage(err, "The workflow couldn't be started"));
    } finally {
      setRunning(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-foreground/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[min(40rem,calc(100dvh-2rem))] w-[min(32rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-container border border-border bg-surface-elevated shadow-elevated focus:outline-none">
          <div className="border-b border-border px-5 py-4">
            <Dialog.Title className="text-[15px] font-semibold text-foreground">Run a workflow on this case</Dialog.Title>
            <Dialog.Description className="mt-1 text-[13px] text-text-secondary">
              Pick a workflow and describe the outcome you want. It runs with this conversation as context.
            </Dialog.Description>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
            {launcher.loading ? <p className="text-[13px] text-text-secondary">Loading workflows…</p> : null}
            {!launcher.loading && launcher.templates.length === 0 ? (
              <p className="text-[13px] text-text-secondary">No workflows are set up yet. Add one in Automations.</p>
            ) : null}
            <ul className="space-y-1.5" role="radiogroup" aria-label="Workflow">
              {launcher.templates.map((template) => (
                <li key={template.id}>
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selected === template.id}
                    onClick={() => {
                      setSelected(template.id);
                      if (!request.trim()) setRequest(template.description || template.name);
                    }}
                    className={cn(
                      "w-full rounded-control border px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                      selected === template.id ? "border-primary bg-primary/[0.06]" : "border-border hover:bg-muted",
                    )}
                  >
                    <span className="block text-[13px] font-medium text-foreground">{template.name}</span>
                    {template.description ? <span className="mt-0.5 line-clamp-2 block text-[12px] text-text-secondary">{template.description}</span> : null}
                  </button>
                </li>
              ))}
            </ul>

            <label className="mt-4 block">
              <span className="text-[12px] font-medium text-text-secondary">What should it do?</span>
              <textarea
                value={request}
                onChange={(event) => setRequest(event.target.value)}
                rows={3}
                placeholder="For example: check the delivery status and prepare a reply"
                className="mt-1 block w-full resize-none rounded-control border border-border bg-surface px-3 py-2 text-[13px] outline-none focus:border-focus focus:ring-2 focus:ring-focus/30"
              />
            </label>
            {error ? <p role="alert" className="mt-2 text-[12.5px] text-danger">{error}</p> : null}
          </div>

          <div className="flex justify-end gap-2 border-t border-border px-5 py-3">
            <Dialog.Close asChild>
              <Button variant="secondary" size="sm" disabled={running}>Cancel</Button>
            </Dialog.Close>
            <Button size="sm" disabled={!selected || !request.trim() || running} onClick={() => void start()}>
              {running ? "Starting…" : "Start workflow"}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
