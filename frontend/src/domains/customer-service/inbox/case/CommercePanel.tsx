"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Ban, ChevronDown, ChevronUp, Copy, DollarSign, ExternalLink, MoreHorizontal, Plus, Search, ShoppingCart, SlidersHorizontal, X } from "lucide-react";

import { customerServiceApi } from "@/domains/customer-service/api";
import type {
  ConversationContext,
  ConversationDetail,
  CustomerSummary,
  ShopifyActionResponse,
  ShopifyOrder,
  SuggestedAction,
} from "@/domains/customer-service/model";
import { apiErrorMessage } from "@/platform/api/client";
import { Events, usePublish } from "@/platform/events";
import { ConfirmDialog } from "@/ui/overlay/ConfirmDialog";
import { Button } from "@/ui/primitives/button";

import type { OrderReference } from "../utils/orderRef";
import { pendingSuggestions, suggestionCapability } from "./caseState";
import { formatDay, formatMoney, humanize, lower } from "./format";
import { Field, Section, ToneChip } from "./parts";
import type { useSuggestionDecision } from "./useSuggestionDecision";

type LineItem = { id?: number | string; title?: string; variant_title?: string | null; quantity?: number; price?: string; sku?: string | null };

const ORDER_SOURCE: Record<OrderReference["source"], string> = {
  insight: "Found by Tajeran in the conversation",
  suggestion: "From Tajeran's suggestion",
  message: "Mentioned in a message",
};

type Props = {
  conversation: ConversationDetail;
  context: ConversationContext | null;
  customerSummary: CustomerSummary | null;
  orderRef: OrderReference | null;
  order: ShopifyOrder | null;
  orderLoading: boolean;
  orderError: string | null;
  decision: ReturnType<typeof useSuggestionDecision>;
};

function addressLines(address: Record<string, unknown> | null | undefined) {
  if (!address) return [];
  const text = (key: string) => (typeof address[key] === "string" && address[key] ? String(address[key]) : null);
  return [
    text("name"),
    [text("address1"), text("address2")].filter(Boolean).join(", ") || null,
    [text("city"), text("province_code") ?? text("province"), text("zip")].filter(Boolean).join(" ") || null,
    text("country"),
  ].filter((line): line is string => !!line);
}

// Only rendered when a workflow-backed suggestion makes the action possible.
function SuggestedOrderAction({ suggestion, decision }: { suggestion: SuggestedAction; decision: Props["decision"] }) {
  const [confirming, setConfirming] = useState(false);
  const capability = suggestionCapability(suggestion);
  if (capability.mode !== "execute") return null;
  const busy = decision.busyId === suggestion.id;

  return (
    <>
      <Button size="sm" className="w-full justify-start" disabled={busy} onClick={() => setConfirming(true)}>
        {busy ? "Working…" : capability.label}
      </Button>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`${capability.label}?`}
        description={capability.confirm ?? ""}
        confirmLabel={capability.label}
        busy={busy}
        onConfirm={async () => {
          if (await decision.execute(suggestion)) setConfirming(false);
        }}
      />
    </>
  );
}

function ShippingStatus({ orderRef }: { orderRef: string }) {
  const [result, setResult] = useState<ShopifyActionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const check = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await customerServiceApi.shopifyShippingStatus(orderRef));
    } catch (err) {
      setError(apiErrorMessage(err, "Could not check shipping status"));
    } finally {
      setBusy(false);
    }
  };

  const payload = result?.payload ?? {};
  const text = (key: string) => (typeof payload[key] === "string" && payload[key] ? String(payload[key]) : null);
  const trackingNumber = text("tracking_number");
  const trackingUrl = text("tracking_url");
  const carrier = text("tracking_company");

  return (
    <div>
      <Button variant="secondary" size="sm" className="w-full justify-start" disabled={busy} onClick={() => void check()}>
        {busy ? "Checking Shopify…" : result ? "Check again" : "Check shipping status"}
      </Button>
      {result ? (
        <div className="mt-2 rounded-control bg-muted px-2.5 py-2 text-[12.5px]">
          {payload.status === "found" ? (
            <dl>
              <Field label="Fulfillment">{humanize(text("fulfillment_status") ?? "unknown")}</Field>
              {carrier ? <Field label="Carrier">{carrier}</Field> : null}
              {trackingNumber ? (
                <Field label="Tracking">
                  {trackingUrl ? (
                    <a href={trackingUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                      {trackingNumber}
                      <ExternalLink size={12} aria-hidden />
                    </a>
                  ) : trackingNumber}
                </Field>
              ) : null}
            </dl>
          ) : (
            <p className="text-foreground">No shipment yet. Shopify has no fulfillment for this order.</p>
          )}
        </div>
      ) : null}
      {error ? <p role="alert" className="mt-1 text-[12px] text-danger">{error}</p> : null}
    </div>
  );
}

function Allowed({ label, allowed }: { label: string; allowed: boolean }) {
  return (
    <li className="flex items-center justify-between gap-2">
      <span className="text-foreground">{label}</span>
      <span className={allowed ? "text-commerce-accent" : "text-text-secondary"}>{allowed ? "Allowed" : "Not allowed"}</span>
    </li>
  );
}

function OrderActionDialog({
  open,
  onOpenChange,
  kind,
  orderName,
  total,
  busy,
  available,
  items,
  currency,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  kind: "refund" | "cancel";
  orderName: string;
  total: string;
  busy: boolean;
  available: boolean;
  items: LineItem[];
  currency: string | null | undefined;
  onConfirm: (details: { reason: string; amount: string; item_quantities: Record<string, number>; restock: boolean; notify_customer: boolean; refund_method: string; custom_reason: string }) => void;
}) {
  const [reason, setReason] = useState("");
  const [amount, setAmount] = useState("0.00");
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [restock, setRestock] = useState(false);
  const [notifyCustomer, setNotifyCustomer] = useState(true);
  const [refundMethod, setRefundMethod] = useState("Manual");
  const [customReason, setCustomReason] = useState("Other");
  const isRefund = kind === "refund";
  const availableAmount = Number(total.replace(/[^\d.]/g, "")) || 0;
  const currencyCode = currency ?? "USD";
  const money = (value: number) => formatMoney(value, currencyCode) ?? "—";
  const itemQuantities = items.reduce<Record<string, number>>((result, item, index) => {
    const key = String(item.id ?? index);
    result[key] = quantities[key] ?? 0;
    return result;
  }, {});
  const onConfirmDetails = () => onConfirm({ reason, amount, item_quantities: itemQuantities, restock, notify_customer: notifyCustomer, refund_method: refundMethod, custom_reason: customReason });

  useEffect(() => {
    if (open) {
      setReason("");
      setAmount("0.00");
      setQuantities({});
      setRestock(false);
      setNotifyCustomer(true);
      setRefundMethod("Manual");
      setCustomReason("Other");
    }
  }, [open, kind, orderName]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-foreground/35" />
        <Dialog.Content className={`fixed left-1/2 top-1/2 z-50 flex max-h-[min(90dvh,54rem)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-md border border-border bg-surface-elevated shadow-elevated focus:outline-none ${isRefund ? "w-[min(58rem,calc(100vw-1.5rem))]" : "w-[min(34rem,calc(100vw-1.5rem))]"}`}>
          <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3.5">
            <Dialog.Title className="text-[18px] font-semibold text-foreground">{isRefund ? "Refund order" : "Cancel order"}</Dialog.Title>
            <Dialog.Close aria-label="Close" className="rounded p-1.5 text-text-secondary hover:bg-muted"><X size={17} /></Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">{orderName}. Refund requires approval before Shopify is changed.</Dialog.Description>
          {isRefund ? <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="overflow-x-auto">
              <div className="min-w-[610px]">
                <div className="grid grid-cols-[minmax(210px,1fr)_120px_150px_115px] items-center border-b border-border px-5 py-3 text-[10px] font-semibold uppercase tracking-wide text-text-secondary"><span>Product</span><span className="text-right">Item price</span><span className="text-center">Qty</span><span className="text-right">Item total</span></div>
                {items.length ? items.map((item, index) => {
                  const key = String(item.id ?? index);
                  const max = Math.max(0, item.quantity ?? 0);
                  const qty = itemQuantities[key] ?? 0;
                  const unit = Number(item.price ?? 0) || 0;
                  return <div key={key} className="grid min-h-[72px] grid-cols-[minmax(210px,1fr)_120px_150px_115px] items-center border-b border-border px-5 py-2.5">
                    <div className="min-w-0"><p className="truncate font-medium text-primary">{item.title ?? "Item"}</p>{item.variant_title ? <p className="text-[12px] text-text-secondary">{item.variant_title}</p> : null}<p className="text-[12px] text-text-secondary">SKU: {item.sku ?? "—"}</p></div>
                    <span className="text-right tabular-nums">{money(unit)}</span>
                    <div className="flex items-center justify-center gap-1 text-text-secondary"><span>×</span><input type="number" min={0} max={max} value={qty} onChange={(event) => setQuantities((current) => ({ ...current, [key]: Math.min(max, Math.max(0, Number(event.target.value) || 0)) }))} className="h-8 w-[58px] rounded border border-border bg-surface px-2 text-center text-foreground" /><span>/ {max}</span></div>
                    <span className="text-right font-semibold tabular-nums">{money(unit * qty)}</span>
                  </div>;
                }) : <p className="px-5 py-5 text-sm text-text-secondary">No item details are available for this order. You can enter a custom refund amount below.</p>}
              </div>
            </div>
            <div className="grid gap-6 px-5 py-4 md:grid-cols-[1fr_22rem]">
              <div className="space-y-4">
                <label className="flex items-start gap-2 text-[13px] font-medium text-foreground"><input type="checkbox" checked={restock} onChange={(event) => setRestock(event.target.checked)} className="mt-0.5 accent-primary" /><span>Restock items<small className="mt-1 block max-w-md font-normal leading-4 text-text-secondary">The claimed quantity will be restocked back to your store.</small></span></label>
                <label className="flex items-center gap-2 text-[13px] font-medium text-foreground"><input type="checkbox" checked={notifyCustomer} onChange={(event) => setNotifyCustomer(event.target.checked)} className="accent-primary" />Send notification to customer</label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block text-[12px] font-semibold text-foreground">Refund with
                    <select value={refundMethod} onChange={(event) => setRefundMethod(event.target.value)} className="mt-1 h-9 w-full rounded border border-border bg-surface px-2 text-[13px] font-normal"><option>Manual</option><option>Original payment method</option></select>
                  </label>
                  <label className="block text-[12px] font-semibold text-foreground">Reason for refund
                    <select value={reason} onChange={(event) => setReason(event.target.value)} className="mt-1 h-9 w-full rounded border border-border bg-surface px-2 text-[13px] font-normal"><option value="">Select reason</option><option>Customer request</option><option>Damaged item</option><option>Late delivery</option><option>Discount adjustment</option><option>Other</option></select>
                  </label>
                </div>
                <label className="block max-w-sm text-[12px] font-semibold text-foreground">Reason for custom refund amount
                  <select value={customReason} onChange={(event) => setCustomReason(event.target.value)} className="mt-1 h-9 w-full rounded border border-border bg-surface px-2 text-[13px] font-normal"><option>Other</option><option>Price adjustment</option><option>Shipping refund</option><option>Goodwill refund</option></select>
                </label>
              </div>
              <div className="space-y-2 text-[13px]">
                <div className="flex justify-between text-text-secondary"><span>Subtotal</span><span className="font-semibold text-foreground">{money(items.reduce((sum, item, index) => sum + Number(item.price ?? 0) * (itemQuantities[String(item.id ?? index)] ?? 0), 0))}</span></div>
                <div className="flex justify-between text-text-secondary"><span>Discounts</span><span>—</span></div><div className="flex justify-between text-text-secondary"><span>Tax</span><span>—</span></div>
                <label className="mt-2 block text-text-secondary">Refund amount
                  <div className="mt-1 flex h-9 items-center rounded border border-border bg-surface px-2"><span>{currencyCode}</span><input value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" className="ml-2 min-w-0 flex-1 bg-transparent text-right font-semibold text-foreground outline-none" /></div>
                </label>
                <p className="flex justify-between pt-1 font-medium text-text-secondary"><span>Total available to refund</span><span className="font-semibold text-foreground">{money(availableAmount)}</span></p>
              </div>
            </div>
            <p className="mx-5 mb-4 rounded-control bg-warning/10 px-3 py-2 text-xs leading-5 text-text-secondary">{available ? "This submits a refund request for admin approval. No Shopify refund occurs until approval." : "Generate a Shopify refund suggestion from Decide before submitting this request."}</p>
          </div> : <div className="space-y-4 p-5"><p className="text-sm text-text-secondary">Cancel {orderName} ({total})? This creates an approval request; Shopify is not changed until an authorized person approves it.</p><label className="block text-sm font-medium text-foreground">Reason<select value={reason} onChange={(event) => setReason(event.target.value)} className="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2.5"><option value="">Select a reason</option><option>Customer requested</option><option>Fraud risk</option><option>Out of stock</option></select></label></div>}
          <div className="flex shrink-0 justify-between gap-2 border-t border-border bg-muted/60 px-4 py-3"><Button variant="secondary" size="sm" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button><Button variant={isRefund ? "primary" : "danger"} size="sm" disabled={busy || !reason || !available || (isRefund && !(Number(amount) > 0))} onClick={onConfirmDetails}>{busy ? "Submitting…" : isRefund ? `Refund ${money(Number(amount) || 0)}` : "Start cancellation approval"}</Button></div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Tags({ conversationId, tags }: { conversationId: string; tags: string[] }) {
  const publish = usePublish();
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutate = async (work: () => Promise<unknown>) => {
    setError(null);
    try {
      await work();
      publish({ type: Events.ConversationChanged, payload: { conversationId } });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not update tags"));
    }
  };

  return (
    <div>
      <ul className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <li key={tag} className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-px text-[12px] text-foreground">
            {tag}
            <button
              type="button"
              aria-label={`Remove tag ${tag}`}
              onClick={() => void mutate(() => customerServiceApi.removeTag(conversationId, tag))}
              className="rounded-full text-text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <X size={12} />
            </button>
          </li>
        ))}
      </ul>
      <form
        className="mt-2 flex gap-1.5"
        onSubmit={(event) => {
          event.preventDefault();
          const name = draft.trim();
          if (!name) return;
          setDraft("");
          void mutate(() => customerServiceApi.addTag(conversationId, name));
        }}
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Add a tag"
          aria-label="Add a tag"
          className="h-8 min-w-0 flex-1 rounded-control border border-border bg-surface px-2 text-[13px] outline-none focus:border-focus focus:ring-2 focus:ring-focus/30"
        />
        <Button type="submit" variant="secondary" size="sm" aria-label="Add tag" disabled={!draft.trim()}>
          <Plus size={14} />
        </Button>
      </form>
      {error ? <p role="alert" className="mt-1 text-[12px] text-danger">{error}</p> : null}
    </div>
  );
}

export function CommercePanel({ conversation, context, customerSummary, orderRef, order, orderLoading, orderError, decision }: Props) {
  const customer = context?.customer ?? conversation.customer;
  const ctx = order?.context ?? null;
  const items = ((ctx?.raw?.line_items as LineItem[] | undefined) ?? []).slice(0, 8);
  const tracking = ctx?.tracking;
  const shipTo = addressLines(ctx?.shipping_address);
  const pending = pendingSuggestions(context);
  const matchesOrder = (action: SuggestedAction) =>
    !action.payload?.order_ref || !orderRef || action.payload.order_ref === orderRef.ref;
  const financial = lower(ctx?.financial_status);
  const fulfillment = lower(ctx?.fulfillment_status) || "unfulfilled";
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState({ cart: true, shopify: true, order: true });
  const [action, setAction] = useState<"refund" | "cancel" | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [generatedSuggestions, setGeneratedSuggestions] = useState<SuggestedAction[]>([]);
  const publish = usePublish();
  const allPending = [...pending, ...generatedSuggestions.filter((candidate) => !pending.some((item) => item.id === candidate.id))];
  const refundSuggestion = allPending.find((a) => a.action_type === "shopify_refund" && matchesOrder(a));
  const cancelSuggestion = allPending.find((a) => a.action_type === "shopify_cancel" && matchesOrder(a));
  const orderName = order?.order_name ?? ctx?.order_name ?? orderRef?.ref ?? "Order";
  const total = formatMoney(ctx?.total_price, ctx?.currency) ?? "—";
  const toggle = (key: keyof typeof expanded) => setExpanded((value) => ({ ...value, [key]: !value[key] }));
  const openOrderAction = async (kind: "refund" | "cancel") => {
    const existing = kind === "refund" ? refundSuggestion : cancelSuggestion;
    if (!existing) {
      try {
        const created = await customerServiceApi.generateSuggestedActions(conversation.id);
        setGeneratedSuggestions(created);
        publish({ type: Events.SuggestedActionsChanged, payload: { conversationId: conversation.id } });
      } catch {
        // The dialog remains useful and explains that an approval suggestion is required.
      }
    }
    setAction(kind);
  };
  const initialsText = (customer?.name ?? "Customer").split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  const totalItems = items.reduce((sum, item) => sum + (item.quantity ?? 1), 0);

  return (
    <div className="min-h-full bg-muted/40 text-[13px]">
      <div className="sticky top-0 z-10 border-b border-border bg-surface px-3 py-2">
        <div className="flex items-center gap-2">
          <div className="relative min-w-0 flex-1"><Search size={14} className="absolute left-2.5 top-2.5 text-text-secondary" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search customers or orders" className="h-9 w-full rounded-control border border-border bg-surface pl-8 pr-2 text-[12px] outline-none focus:border-focus" /></div>
          <button type="button" className="inline-flex h-9 w-9 items-center justify-center rounded-control border border-border bg-surface text-text-secondary hover:bg-muted" aria-label="Customer panel settings"><SlidersHorizontal size={16} /></button>
        </div>
      </div>

      <div className="border-b border-border bg-surface px-3 py-3">
        <div className="flex items-start gap-2.5">
          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-sm bg-[#f28b82] font-bold text-white">{initialsText || "CU"}</span>
          <div className="min-w-0"><p className="truncate text-[15px] font-semibold text-foreground">{customer?.name || "Name not provided"}</p><p className="mt-1 text-[12px] text-text-secondary">▰ This customer has no note.</p>{customer?.email ? <a href={`mailto:${customer.email}`} className="mt-1 block truncate text-[12px] text-primary hover:underline">✉ {customer.email}</a> : null}</div>
        </div>
        <button type="button" onClick={() => setTimelineOpen((value) => !value)} className="mt-2 text-[12px] font-medium text-primary">{timelineOpen ? "Show Less⌃" : "Show More⌄"}</button>
        {timelineOpen ? <div className="mt-2 rounded-control bg-muted p-2 text-[12px] text-text-secondary"><p>Conversations: {customerSummary?.conversation_count ?? 0}</p><p>Tickets: {customerSummary?.ticket_count ?? 0}</p><button type="button" className="mt-2 rounded-control border border-border bg-surface px-2 py-1 font-medium text-foreground">☷ Customer Timeline</button></div> : null}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-2 border-b border-border bg-surface px-3 py-2 text-[11px] font-semibold text-text-secondary"><span className="text-commerce-accent">Shopify</span><span>Bloomreach Engagement</span><span>Loop Returns</span><span>Smile</span><span>Yotpo</span></div>

      <div className="space-y-2 p-2">
        <div className="rounded-control border border-border bg-surface shadow-sm">
          <button type="button" onClick={() => toggle("cart")} className="flex w-full items-center justify-between px-3 py-2.5 text-left font-semibold text-foreground"><span className="inline-flex items-center gap-2"><ShoppingCart size={14} /> Cart</span>{expanded.cart ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button>
          {expanded.cart ? <div className="grid grid-cols-2 gap-2 border-t border-border px-3 py-2.5"><div><p className="text-text-secondary">Items:</p><p className="mt-1 font-semibold">{totalItems || 0}</p></div><div><p className="text-text-secondary">Total:</p><p className="mt-1 font-semibold">{total}</p></div></div> : null}
        </div>

        <div className="rounded-control border border-border bg-surface shadow-sm">
          <button type="button" onClick={() => toggle("shopify")} className="flex w-full items-center justify-between px-3 py-2.5 text-left font-semibold text-foreground"><span><span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded bg-[#95bf47] text-[11px] font-bold text-white">S</span>Shopify <span className="ml-1 text-primary">{customer?.name || "Customer"}</span></span>{expanded.shopify ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button>
          {expanded.shopify ? <div className="border-t border-border px-3 pb-3 pt-2.5"><Button variant="secondary" size="sm" className="h-8 w-full text-[12px]" disabled title="Order creation will be enabled with the Shopify draft-order workflow"><Plus size={13} /> Create Order</Button><dl className="mt-2.5"><Field label="Total spent">{total}</Field><Field label="Orders">{customerSummary?.conversation_count ? 1 : 0}</Field><Field label="Created at">{customerSummary?.first_seen_at ? formatDay(customerSummary.first_seen_at) : "—"}</Field><Field label="Note">—</Field><Field label="Tags">{(context?.tags ?? []).map((tag) => tag.name).join(", ") || "Add tags…"}</Field></dl></div> : null}
        </div>

        {orderRef && order && ctx ? <div className="rounded-control border border-border bg-surface shadow-sm">
          <button type="button" onClick={() => toggle("order")} className="flex w-full items-center justify-between px-3 py-2.5 text-left"><span className="text-[15px] font-semibold text-primary">{orderName}</span>{expanded.order ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button>
          {expanded.order ? <div className="border-t border-border px-3 pb-2.5 pt-2"><div className="flex flex-wrap gap-1.5"><ToneChip tone={ctx.is_paid ? "commerce" : "neutral"}>{humanize(financial || "unknown")}</ToneChip><ToneChip tone={ctx.is_fulfilled ? "commerce" : "neutral"}>{humanize(fulfillment)}</ToneChip></div><div className="mt-2 flex items-center gap-1 overflow-x-auto"><Button variant="secondary" size="sm" className="h-8 shrink-0 px-2 text-[11px]" title="Duplicate order"><Copy size={12} /> Duplicate</Button><Button variant="secondary" size="sm" className="h-8 shrink-0 px-2 text-[11px]" disabled={!ctx.can_refund} onClick={() => void openOrderAction("refund")}><DollarSign size={12} /> Refund</Button><Button variant="secondary" size="sm" className="h-8 shrink-0 px-2 text-[11px]" disabled={!ctx.can_cancel} onClick={() => void openOrderAction("cancel")}><Ban size={12} /> Cancel</Button><button type="button" onClick={() => setMoreOpen((value) => !value)} className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-border text-text-secondary" aria-label="More order actions"><MoreHorizontal size={15} /></button></div>{moreOpen ? <div className="mt-2 rounded-control bg-muted p-2 text-xs text-text-secondary"><p>Change address: {ctx.can_change_address ? "Available with approval" : "Not available"}</p><ShippingStatus orderRef={orderRef.ref} /></div> : null}</div> : null}
        </div> : orderLoading ? <div className="rounded-control border border-border bg-surface p-3 text-text-secondary">Loading order…</div> : orderError ? <div className="rounded-control border border-danger/30 bg-surface p-3 text-danger">{orderError}</div> : null}

        <div className="rounded-control border border-border bg-surface p-3"><div className="mb-2 flex items-center justify-between"><h3 className="font-semibold text-foreground">Tags</h3><span className="text-[11px] text-text-secondary">Conversation</span></div><Tags conversationId={conversation.id} tags={(context?.tags ?? []).map((tag) => tag.name)} /></div>
      </div>
      {order && ctx && orderRef ? <><OrderActionDialog open={action === "refund"} onOpenChange={(open) => !open && setAction(null)} kind="refund" orderName={orderName} total={total} available={Boolean(refundSuggestion)} items={items} currency={ctx.currency} busy={decision.busyId === refundSuggestion?.id} onConfirm={(details) => { if (refundSuggestion) void decision.execute(refundSuggestion, details).then((ok) => ok && setAction(null)); }} /><OrderActionDialog open={action === "cancel"} onOpenChange={(open) => !open && setAction(null)} kind="cancel" orderName={orderName} total={total} available={Boolean(cancelSuggestion)} items={items} currency={ctx.currency} busy={decision.busyId === cancelSuggestion?.id} onConfirm={({ reason }) => { if (cancelSuggestion) void decision.execute(cancelSuggestion, { reason }).then((ok) => ok && setAction(null)); }} /></> : null}
    </div>
  );
}
