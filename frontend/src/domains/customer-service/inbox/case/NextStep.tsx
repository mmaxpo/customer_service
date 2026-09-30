"use client";

import { useState } from "react";
import Link from "next/link";
import { CircleAlert } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import { customerServiceApi } from "@/domains/customer-service/api";
import { apiErrorMessage } from "@/platform/api/client";
import { Events, usePublish } from "@/platform/events";
import { TajeranMark } from "@/ui/brand/TajeranMark";
import { ConfirmDialog } from "@/ui/overlay/ConfirmDialog";
import { Button } from "@/ui/primitives/button";

import { suggestionCapability, type NextStep as Step } from "./caseState";
import { humanize } from "./format";
import type { useSuggestionDecision } from "./useSuggestionDecision";

type Props = {
  step: Step | null;
  conversationId: string;
  decision: ReturnType<typeof useSuggestionDecision>;
};

function SuggestionStep({ step, decision }: { step: Extract<Step, { kind: "suggestion" }>; decision: Props["decision"] }) {
  const [confirming, setConfirming] = useState(false);
  const { action } = step;
  const capability = suggestionCapability(action);
  const busy = decision.busyId === action.id;
  const reason = typeof action.payload?.reason === "string" ? action.payload.reason : action.description;

  const execute = async () => {
    const ok = await decision.execute(action);
    if (ok) setConfirming(false);
  };

  return (
    <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center">
      <div className="flex min-w-0 flex-1 gap-2.5">
        <TajeranMark variant="actor" size={20} className="mt-px" />
        <div className="min-w-0">
          <p className="text-[13px] font-medium text-foreground">
            Tajeran suggests: {action.title}
            {step.more > 0 ? <span className="ml-2 font-normal text-text-secondary">+{step.more} more in the timeline</span> : null}
          </p>
          {reason ? <p className="mt-0.5 line-clamp-2 text-[12.5px] text-text-secondary">{reason}</p> : null}
          {capability.mode === "accept" ? <p className="mt-0.5 text-[12px] text-text-secondary">{capability.reason}</p> : null}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1.5 pl-7 sm:pl-0">
        <Button variant="ghost" size="sm" disabled={busy} onClick={() => void decision.dismiss(action)}>
          Dismiss
        </Button>
        {capability.mode === "execute" ? (
          <Button
            size="sm"
            disabled={busy}
            onClick={() => (capability.confirm ? setConfirming(true) : void execute())}
          >
            {busy ? "Working…" : capability.label}
          </Button>
        ) : (
          <Button variant="secondary" size="sm" disabled={busy} onClick={() => void decision.accept(action)}>
            {busy ? "Working…" : "Accept"}
          </Button>
        )}
      </div>

      {capability.mode === "execute" && capability.confirm ? (
        <ConfirmDialog
          open={confirming}
          onOpenChange={setConfirming}
          title={`${capability.label}?`}
          description={capability.confirm}
          confirmLabel={capability.label}
          busy={busy}
          onConfirm={() => void execute()}
        />
      ) : null}
    </div>
  );
}

export function NextStep({ step, conversationId, decision }: Props) {
  const publish = usePublish();
  const [resolving, setResolving] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);

  const resolve = async (ticketId: string) => {
    setResolving(true);
    setResolveError(null);
    try {
      await customerServiceApi.updateTicket(ticketId, { status: "resolved" });
      publish({ type: Events.ConversationChanged, payload: { conversationId } });
    } catch (err) {
      setResolveError(apiErrorMessage(err, "Could not resolve the case"));
    } finally {
      setResolving(false);
    }
  };

  const error = decision.error ?? resolveError;

  return (
    <AnimatePresence initial={false} mode="wait">
      {step ? (
        <motion.div
          key={step.kind === "suggestion" ? step.action.id : step.kind}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.15 }}
          className="shrink-0 border-t border-border bg-surface px-4 py-3 sm:px-5"
          aria-label="Next step"
          role="region"
        >
          {step.kind === "suggestion" ? <SuggestionStep step={step} decision={decision} /> : null}

          {step.kind === "failed" ? (
            <div className="flex items-start gap-2.5">
              <CircleAlert size={18} className="mt-px shrink-0 text-danger" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium text-foreground">
                  Workflow failed: {step.execution.workflow_name ?? step.execution.template_name ?? humanize(step.execution.job_type ?? "workflow")}
                </p>
                {step.execution.error_message ? (
                  <p className="mt-0.5 line-clamp-2 text-[12.5px] text-text-secondary">{step.execution.error_message}</p>
                ) : null}
              </div>
              {step.execution.workflow_run_id ? (
                <Link
                  href={`/app/runs/${step.execution.workflow_run_id}`}
                  className="shrink-0 rounded-control px-2 py-1 text-[13px] font-medium text-primary hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                >
                  View run
                </Link>
              ) : null}
            </div>
          ) : null}

          {step.kind === "resolve" ? (
            <div className="flex items-center gap-3">
              <p className="min-w-0 flex-1 text-[13px] text-text-secondary">The customer has the latest reply. Resolve the case when nothing else is needed.</p>
              <Button size="sm" disabled={resolving} onClick={() => void resolve(step.ticketId)}>
                {resolving ? "Resolving…" : "Mark resolved"}
              </Button>
            </div>
          ) : null}

          {error ? <p role="alert" className="mt-2 text-[12.5px] text-danger">{error}</p> : null}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
