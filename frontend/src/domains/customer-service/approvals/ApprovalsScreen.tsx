"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, X } from "lucide-react";
import { AnimatePresence, MotionConfig, motion } from "motion/react";

import type { ReviewPlan, ReviewPlanOperation, WorkflowWait } from "@/domains/customer-service/model";
import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";
import { ConfirmDialog } from "@/ui/overlay/ConfirmDialog";

import { formatDay, formatMoney, formatTime, humanize } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import { useApprovals } from "../inbox/features/approvals/hooks";
import { useCommerceOrder } from "../inbox/features/commerce/hooks";

type Decided = { id: string; approved: boolean; summary: string; at: string };

const FINANCIAL = new Set(["whole_refund", "partial_refund", "item_refund", "refund", "cancel", "cancel_order", "reship"]);

const record = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

// The approval node stores its context under a configurable key; real waits use "context".
function reviewPlanOf(wait: WorkflowWait): ReviewPlan | null {
  const contextKey = typeof wait.payload.context_payload_key === "string" ? wait.payload.context_payload_key : "context";
  const plan = record(record(wait.payload[contextKey]).review_plan);
  return Object.keys(plan).length ? (plan as ReviewPlan) : null;
}

function operationLabel(operation: ReviewPlanOperation) {
  switch (operation.operation_type) {
    case "whole_refund":
      return "Refund the whole order";
    case "partial_refund":
    case "item_refund":
      return `Refund ${operation.item_label ?? "part of the order"}`;
    case "cancel":
    case "cancel_order":
      return "Cancel the order";
    case "reship":
      return `Reship ${operation.item_label ?? "the order"}`;
    case "update_shipping_address":
    case "change_address":
      return "Change the shipping address";
    default:
      return humanize(operation.operation_type);
  }
}

function approveLabel(operations: ReviewPlanOperation[]) {
  if (operations.length !== 1) return "Approve";
  const type = operations[0].operation_type;
  if (type.includes("refund")) return "Approve refund";
  if (type.includes("cancel")) return "Approve cancellation";
  if (type === "reship") return "Approve reship";
  if (type.includes("address")) return "Approve address change";
  return "Approve";
}

type LineItem = { id?: string | number; title?: string; quantity?: number; price?: string };

function ApprovalItem({
  wait,
  busy,
  onDecide,
}: {
  wait: WorkflowWait;
  busy: boolean;
  onDecide: (wait: WorkflowWait, approved: boolean, summary: string) => Promise<string | null>;
}) {
  const [confirm, setConfirm] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const plan = reviewPlanOf(wait);
  const operations = plan?.operations ?? [];
  const orderRef = plan?.order_ref ?? null;
  const { order, loading: orderLoading, error: orderError } = useCommerceOrder(orderRef);
  const ctx = order?.context ?? null;
  const total = ctx ? formatMoney(ctx.total_price, ctx.currency) : null;
  const wholeRefundOnly = operations.length > 0 && operations.every((op) => op.operation_type === "whole_refund");
  const items = ((ctx?.raw?.line_items as LineItem[] | undefined) ?? []).slice(0, 6);
  const question = typeof wait.payload.question === "string" ? wait.payload.question : "Approval needed";
  const financial = operations.some((op) => FINANCIAL.has(op.operation_type));
  const label = approveLabel(operations);
  const summary = operations.length ? operations.map(operationLabel).join(", ") : question;

  const decide = async (approved: boolean) => {
    setError(null);
    const failure = await onDecide(wait, approved, `${summary}${orderRef ? ` for order ${orderRef}` : ""}`);
    if (failure) setError(failure);
    setConfirm(null);
  };

  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0, marginTop: 0, transition: { duration: 0.2 } }}
      className="overflow-hidden rounded-container border border-warning/40 bg-surface"
    >
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <ToneChip tone="attention">Waiting for a decision</ToneChip>
            <span className="text-[12px] text-text-secondary">
              Requested {formatDay(wait.created_at)} at {formatTime(wait.created_at)}
              {wait.expires_at ? `, expires ${formatDay(wait.expires_at)} ${formatTime(wait.expires_at)}` : ""}
            </span>
          </div>
          <h2 className="mt-2 text-[15px] font-semibold text-foreground">{question}</h2>

          {operations.length ? (
            <ul className="mt-2 space-y-0.5 text-[14px] text-foreground">
              {operations.map((operation, index) => (
                <li key={operation.operation_ref ?? index}>{operationLabel(operation)}</li>
              ))}
            </ul>
          ) : null}

          <dl className="mt-3 grid max-w-md grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-[13px]">
            {orderRef ? (
              <>
                <dt className="text-text-secondary">Order</dt>
                <dd className="text-foreground">
                  {orderRef}
                  {plan?.provider ? <span className="text-text-secondary"> in {humanize(plan.provider)}</span> : null}
                </dd>
              </>
            ) : null}
            {ctx ? (
              <>
                <dt className="text-text-secondary">{wholeRefundOnly ? "Order total" : "Order value"}</dt>
                <dd className="tabular-nums text-foreground">{total ?? "Not available"}</dd>
                <dt className="text-text-secondary">Order status</dt>
                <dd className="text-foreground">
                  {humanize(ctx.financial_status ?? "unknown")}, {humanize(ctx.fulfillment_status ?? "unfulfilled").toLowerCase()}
                </dd>
              </>
            ) : orderRef && orderLoading ? (
              <>
                <dt className="text-text-secondary">Order value</dt>
                <dd className="text-text-secondary">Loading…</dd>
              </>
            ) : orderRef && orderError ? (
              <>
                <dt className="text-text-secondary">Order value</dt>
                <dd className="text-text-secondary">Couldn&apos;t load the order ({orderError})</dd>
              </>
            ) : null}
          </dl>

          {items.length ? (
            <ul className="mt-3 max-w-md space-y-1 border-t border-border pt-2.5 text-[13px]">
              {items.map((item, index) => (
                <li key={item.id ?? index} className="flex justify-between gap-3">
                  <span className="text-foreground">
                    {item.title ?? "Item"}
                    {item.quantity && item.quantity > 1 ? <span className="text-text-secondary"> × {item.quantity}</span> : null}
                  </span>
                  {item.price ? <span className="tabular-nums text-text-secondary">{formatMoney(item.price, ctx?.currency)}</span> : null}
                </li>
              ))}
            </ul>
          ) : null}

          <p className="mt-3 text-[12.5px] text-text-secondary">
            Approving resumes the workflow so it can carry out {operations.length === 1 ? "this change" : "these changes"}. Rejecting resumes it with the change declined.{" "}
            <Link href={`/app/runs/${wait.workflow_run_id}`} className="font-medium text-primary hover:underline">
              View workflow run
            </Link>
          </p>
          {error ? <p role="alert" className="mt-2 text-[12.5px] text-danger">{error}</p> : null}
        </div>

        <div className="flex shrink-0 gap-2 sm:flex-col sm:items-stretch">
          <Button size="sm" disabled={busy} onClick={() => setConfirm("approve")}>{label}</Button>
          <Button variant="secondary" size="sm" disabled={busy} onClick={() => setConfirm("reject")}>Reject</Button>
        </div>
      </div>

      <ConfirmDialog
        open={confirm === "approve"}
        onOpenChange={(open) => setConfirm(open ? "approve" : null)}
        title={`${label}?`}
        description={
          <>
            <p>{summary}{orderRef ? ` for order ${orderRef}` : ""}{wholeRefundOnly && total ? ` (order total ${total})` : ""}.</p>
            <p className="mt-2">
              {financial ? "The workflow resumes and can make this change in Shopify." : "The workflow resumes with your approval."}
            </p>
          </>
        }
        confirmLabel={label}
        busy={busy}
        onConfirm={() => void decide(true)}
      />
      <ConfirmDialog
        open={confirm === "reject"}
        onOpenChange={(open) => setConfirm(open ? "reject" : null)}
        title="Reject this request?"
        description={<p>The workflow resumes with this change declined: {summary.toLowerCase()}{orderRef ? ` for order ${orderRef}` : ""}.</p>}
        confirmLabel="Reject"
        tone="danger"
        busy={busy}
        onConfirm={() => void decide(false)}
      />
    </motion.li>
  );
}

export default function ApprovalsScreen() {
  const { waits, loading, error, mutatingId, approve, reject } = useApprovals();
  const [decided, setDecided] = useState<Decided[]>([]);

  const onDecide = async (wait: WorkflowWait, approved: boolean, summary: string) => {
    try {
      await (approved ? approve(wait.id) : reject(wait.id));
      setDecided((list) => [{ id: wait.id, approved, summary, at: new Date().toISOString() }, ...list]);
      return null;
    } catch (err) {
      return apiErrorMessage(err, "The decision couldn't be saved. Try again.");
    }
  };

  return (
    <MotionConfig reducedMotion="user">
      <div className="min-h-0 flex-1 overflow-y-auto bg-background">
        <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6">
          <header className="mb-5">
            <h1 className="text-[18px] font-semibold text-foreground">Approvals</h1>
            <p className="mt-1 max-w-2xl text-[13.5px] text-text-secondary">
              Workflows pause here when they need a person&apos;s decision before changing anything, such as a refund in Shopify.
            </p>
          </header>

          {error ? <p role="alert" className="mb-4 text-[13px] text-danger">{error}</p> : null}

          {loading ? (
            <div className="h-40 rounded-container border border-border bg-surface" aria-hidden />
          ) : waits.length === 0 ? (
            <div className="rounded-container border border-border bg-surface px-5 py-8 text-center">
              <p className="text-[14px] font-medium text-foreground">Nothing is waiting for approval</p>
              <p className="mt-1 text-[13px] text-text-secondary">New requests appear here as soon as a workflow pauses for a decision.</p>
            </div>
          ) : (
            <ul className="space-y-3" aria-label="Waiting approvals">
              <AnimatePresence initial={false}>
                {waits.map((wait) => (
                  <ApprovalItem key={wait.id} wait={wait} busy={mutatingId === wait.id} onDecide={onDecide} />
                ))}
              </AnimatePresence>
            </ul>
          )}

          {decided.length ? (
            <section className="mt-8" aria-label="Decided in this session">
              <h2 className="mb-2 text-[12px] font-semibold text-text-secondary">Decided just now</h2>
              <ul className="divide-y divide-border rounded-container border border-border bg-surface">
                <AnimatePresence initial={false}>
                  {decided.map((item) => (
                    <motion.li
                      key={item.id}
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-[13px]"
                    >
                      {item.approved ? <Check size={15} className="text-foreground" aria-hidden /> : <X size={15} className="text-text-secondary" aria-hidden />}
                      <span className="min-w-0 flex-1 truncate text-foreground">{item.summary}</span>
                      <span className="shrink-0 text-text-secondary">{item.approved ? "Approved" : "Rejected"} at {formatTime(item.at)}</span>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            </section>
          ) : null}
        </div>
      </div>
    </MotionConfig>
  );
}
