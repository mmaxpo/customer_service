"use client";

import { useRef, useState } from "react";
import { ChevronRight, FileText, LoaderCircle, Paperclip, Sparkles, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import type { AIReplyComposeResponse } from "@/domains/customer-service/model";
import { cn } from "@/platform/utils";
import { TajeranMark } from "@/ui/brand/TajeranMark";
import { Button } from "@/ui/primitives/button";

import { humanize } from "../../case/format";

type Props = {
  composerMode: "reply" | "note";
  setComposerMode: (mode: "reply" | "note") => void;
  replyText: string;
  internalNoteText: string;
  setReplyText: (value: string) => void;
  setInternalNoteText: (value: string) => void;
  aiReply: AIReplyComposeResponse | null;
  composeReply: () => void;
  sendReply: () => void;
  addInternalNote: () => void;
  isComposing: boolean;
  isSending: boolean;
  isAddingNote: boolean;
  attachments: { id: string; filename: string; content_type: string; size_bytes: number; scan_status: string }[];
  uploadAttachments: (files: File[]) => Promise<void>;
  removeAttachment: (attachmentId: string) => void;
  isUploading: boolean;
};

type KnowledgeHit = { title?: string | null; filename?: string | null; source?: string | null; content?: string; score?: number | null };

const record = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const MACROS = [
  { label: "Order status", text: "Hi {{customer}}, I’m checking your order status now and will share the latest update shortly." },
  { label: "Refund received", text: "Your refund has been submitted. It can take 3–5 business days to appear with your payment provider." },
  { label: "Shipping delay", text: "I’m sorry for the delay. I’m checking the latest carrier update and will get back to you with the next step." },
];

function DraftSources({ reply }: { reply: AIReplyComposeResponse }) {
  const [open, setOpen] = useState(false);
  const sources = record(reply.sources);
  const hits = (Array.isArray(sources.knowledge_hits) ? sources.knowledge_hits : []) as KnowledgeHit[];
  const shopify = record(sources.shopify_context);
  const order = record(shopify.order);
  const orderName = typeof order.order_name === "string" ? order.order_name : typeof order.name === "string" ? order.name : null;
  const intent = typeof sources.intent === "string" ? sources.intent : null;
  const hasShopify = shopify.found === true;
  const count = hits.length + (hasShopify ? 1 : 0);

  return (
    <div className="border-b border-border px-3 py-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px]">
        <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
          <TajeranMark variant="actor" size={16} />
          Draft by Tajeran
        </span>
        {reply.requires_review ? <span className="text-warning">Review before sending</span> : null}
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="inline-flex items-center gap-0.5 rounded-control font-medium text-text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          <ChevronRight size={13} className={cn("transition-transform", open && "rotate-90")} aria-hidden />
          {count > 0 ? `What it used (${count})` : "What it used"}
        </button>
      </div>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <ul className="mt-2 space-y-2 text-[12px]">
              {intent ? <li className="text-text-secondary">Intent: <span className="text-foreground">{humanize(intent)}</span></li> : null}
              <li className="text-text-secondary">Confidence: <span className="text-foreground tabular-nums">{Math.round(reply.confidence * 100)}%</span></li>
              {hasShopify ? (
                <li className="text-text-secondary">Shopify order context{orderName ? <span className="text-foreground">: {orderName}</span> : null}</li>
              ) : null}
              {hits.map((hit, index) => (
                <li key={`${hit.title ?? hit.filename ?? "hit"}-${index}`} className="rounded-control border border-border px-2 py-1.5">
                  <p className="font-medium text-foreground">{hit.title || hit.filename || hit.source || "Knowledge source"}</p>
                  {hit.content ? <p className="mt-0.5 line-clamp-3 text-text-secondary">{hit.content}</p> : null}
                </li>
              ))}
              {count === 0 ? <li className="text-text-secondary">No knowledge articles or order data were used for this draft.</li> : null}
            </ul>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export function ReplyComposer({
  composerMode,
  setComposerMode,
  replyText,
  internalNoteText,
  setReplyText,
  setInternalNoteText,
  aiReply,
  composeReply,
  sendReply,
  addInternalNote,
  isComposing,
  isSending,
  isAddingNote,
  attachments,
  uploadAttachments,
  removeAttachment,
  isUploading,
}: Props) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [macrosOpen, setMacrosOpen] = useState(false);
  const [aiToolsOpen, setAiToolsOpen] = useState(false);
  const isNote = composerMode === "note";
  const value = isNote ? internalNoteText : replyText;
  const busy = isNote ? isAddingNote : isSending;
  const canSubmit = (value.trim().length > 0 || attachments.length > 0) && !busy && !isUploading;
  const submit = isNote ? addInternalNote : sendReply;

  const chooseMacro = (text: string) => {
    if (isNote) setInternalNoteText(text);
    else setReplyText(text);
    setMacrosOpen(false);
  };

  const rewrite = (mode: "polish" | "shorten" | "expand") => {
    if (!value.trim()) return;
    const next = mode === "shorten"
      ? value.split(/\s+/).slice(0, 32).join(" ").replace(/[,.!?]?$/, "…")
      : mode === "expand"
        ? `${value.trim()}\n\nPlease let us know if there is anything else we can help with.`
        : `Hi there,\n\n${value.trim()}\n\nThanks for reaching out to Tajeran Support.`;
    if (isNote) setInternalNoteText(next);
    else setReplyText(next);
    setAiToolsOpen(false);
  };

  return (
    <div className="shrink-0 border-t border-border bg-surface px-3 pb-3 pt-2 sm:px-4">
      <div role="tablist" aria-label="Composer mode" className="mb-2 flex gap-1">
        {(["reply", "note"] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            role="tab"
            aria-selected={composerMode === mode}
            onClick={() => setComposerMode(mode)}
            className={cn(
              "rounded-control px-2.5 py-1 text-[12.5px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
              composerMode === mode ? "bg-muted text-foreground" : "text-text-secondary hover:text-foreground",
            )}
          >
            {mode === "reply" ? "Reply" : "Internal note"}
          </button>
        ))}
      </div>

      <div
        className={cn(
          "overflow-hidden rounded-container border bg-surface focus-within:border-focus focus-within:ring-2 focus-within:ring-focus/20",
          isNote ? "border-dashed border-border" : "border-border",
        )}
      >
        {!isNote && aiReply ? <DraftSources reply={aiReply} /> : null}
        <textarea
          aria-label={isNote ? "Internal note" : "Reply to customer"}
          value={value}
          onChange={(event) => (isNote ? setInternalNoteText(event.target.value) : setReplyText(event.target.value))}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && canSubmit) {
              event.preventDefault();
              submit();
            }
          }}
          placeholder={isNote ? "Only your team sees internal notes" : "Write a reply to the customer"}
          rows={3}
          className="block max-h-60 min-h-20 w-full resize-y bg-transparent px-3 py-2.5 text-[14px] leading-6 text-foreground outline-none placeholder:text-text-secondary"
        />
        {attachments.length ? (
          <ul className="flex flex-wrap gap-1.5 border-t border-border px-3 py-2" aria-label="Attachments">
            {attachments.map((file) => (
              <li key={file.id} className="inline-flex max-w-full items-center gap-1.5 rounded-control bg-muted px-2 py-1 text-[11.5px] text-foreground">
                <FileText size={13} className="shrink-0 text-text-secondary" aria-hidden />
                <span className="max-w-40 truncate">{file.filename}</span>
                <button type="button" aria-label={`Remove ${file.filename}`} onClick={() => removeAttachment(file.id)} className="text-text-secondary hover:text-foreground"><X size={12} /></button>
              </li>
            ))}
          </ul>
        ) : null}
        <div className="flex items-center justify-between gap-2 border-t border-border px-2 py-1.5">
          <div className="flex items-center gap-0.5">
            <input ref={fileInput} type="file" multiple className="sr-only" onChange={(event) => { void uploadAttachments(Array.from(event.target.files ?? [])); event.currentTarget.value = ""; }} />
            <Button variant="ghost" size="sm" aria-label="Attach files" disabled={isUploading} onClick={() => fileInput.current?.click()} className="px-2 text-text-secondary"><Paperclip size={15} /></Button>
            <div className="relative">
              <Button variant="ghost" size="sm" aria-expanded={macrosOpen} onClick={() => { setMacrosOpen((current) => !current); setAiToolsOpen(false); }} className="gap-1 px-2 text-[12px] text-text-secondary"><FileText size={14} /> Macro</Button>
              {macrosOpen ? <div className="absolute bottom-9 left-0 z-30 w-56 rounded-container border border-border bg-surface-elevated p-1 shadow-elevated">
                {MACROS.map((macro) => <button key={macro.label} type="button" onClick={() => chooseMacro(macro.text)} className="block w-full rounded-control px-2 py-1.5 text-left text-[12px] text-foreground hover:bg-muted">{macro.label}</button>)}
              </div> : null}
            </div>
            <div className="relative">
              <Button variant="ghost" size="sm" aria-expanded={aiToolsOpen} onClick={() => { setAiToolsOpen((current) => !current); setMacrosOpen(false); }} className="gap-1 px-2 text-[12px] text-ai-accent"><Sparkles size={14} /> Rewrite</Button>
              {aiToolsOpen ? <div className="absolute bottom-9 left-0 z-30 w-44 rounded-container border border-border bg-surface-elevated p-1 shadow-elevated">
                <button type="button" disabled={!value.trim()} onClick={() => rewrite("polish")} className="block w-full rounded-control px-2 py-1.5 text-left text-[12px] text-foreground hover:bg-muted disabled:opacity-50">Polish tone</button>
                <button type="button" disabled={!value.trim()} onClick={() => rewrite("shorten")} className="block w-full rounded-control px-2 py-1.5 text-left text-[12px] text-foreground hover:bg-muted disabled:opacity-50">Shorten</button>
                <button type="button" disabled={!value.trim()} onClick={() => rewrite("expand")} className="block w-full rounded-control px-2 py-1.5 text-left text-[12px] text-foreground hover:bg-muted disabled:opacity-50">Add helpful detail</button>
              </div> : null}
            </div>
            {!isNote ? <Button variant="ghost" size="sm" disabled={isComposing} onClick={composeReply} className="gap-1.5 px-2 text-[12px]">
              {isComposing ? <LoaderCircle size={14} className="animate-spin" aria-hidden /> : <TajeranMark variant="actor" size={16} />}
              <span className="hidden sm:inline">{isComposing ? "Drafting…" : aiReply ? "Redraft" : "Draft with Tajeran"}</span>
            </Button> : null}
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden text-[11px] text-text-secondary sm:inline">Ctrl or ⌘ + Enter</span>
            <Button size="sm" variant={canSubmit ? "primary" : "secondary"} disabled={!canSubmit} onClick={submit}>
              {busy ? (isNote ? "Saving…" : "Sending…") : isNote ? "Add note" : "Send reply"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
