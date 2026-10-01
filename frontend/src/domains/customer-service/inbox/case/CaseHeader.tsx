"use client";

import { useEffect, useState } from "react";
import * as Menu from "@radix-ui/react-dropdown-menu";
import { ArrowLeft, Check, ChevronDown, Ellipsis, PanelRight } from "lucide-react";

import { customerServiceApi } from "@/domains/customer-service/api";
import type { Agent, ConversationContext, ConversationDetail } from "@/domains/customer-service/model";
import { apiErrorMessage } from "@/platform/api/client";
import { Events, usePublish } from "@/platform/events";
import { cn } from "@/platform/utils";
import { ConfirmDialog } from "@/ui/overlay/ConfirmDialog";

import type { CaseState } from "./caseState";
import { formatDay, formatTime, humanize, lower } from "./format";
import { ToneChip } from "./parts";
import { RunWorkflowDialog } from "./RunWorkflowDialog";

const STATUSES = ["open", "pending", "resolved"] as const;
const PRIORITIES = ["low", "normal", "high", "urgent"] as const;

const menuContent = "z-50 min-w-48 rounded-container border border-border bg-surface-elevated p-1 text-[13px] shadow-elevated";
const menuItem = "flex cursor-default select-none items-center gap-2 rounded-control px-2 py-1.5 outline-none data-[highlighted]:bg-muted data-[disabled]:opacity-50";

type Props = {
  conversation: ConversationDetail;
  context: ConversationContext | null;
  state: CaseState | null;
  onBack?: () => void;
  onOpenContext: () => void;
  onDelete: () => void;
  deleting: boolean;
};

export function CaseHeader({ conversation, context, state, onBack, onOpenContext, onDelete, deleting }: Props) {
  const publish = usePublish();
  const [error, setError] = useState<string | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [runOpen, setRunOpen] = useState(false);

  const customer = context?.customer ?? conversation.customer;
  const ticket = context?.ticket ?? conversation.ticket;
  const insight = context?.latest_insight ?? null;
  const priority = lower(ticket?.priority);
  const openSla = context?.sla.open[0] ?? null;
  const snoozedUntil = typeof context?.conversation.snoozed_until === "string" ? context.conversation.snoozed_until : null;

  useEffect(() => {
    let active = true;
    void customerServiceApi.agents().then((result) => {
      if (active) setAgents(result);
    }).catch(() => {
      // The unassigned action remains available when no agent directory exists yet.
    });
    return () => { active = false; };
  }, []);

  const changed = () => publish({ type: Events.ConversationChanged, payload: { conversationId: conversation.id } });

  async function run(work: () => Promise<unknown>, fallback: string) {
    setError(null);
    try {
      await work();
      changed();
    } catch (err) {
      setError(apiErrorMessage(err, fallback));
    }
  }

  const updateTicket = (field: "status" | "priority" | "assigned_to", value: string | null) =>
    ticket && run(() => customerServiceApi.updateTicket(ticket.id, { [field]: value }), "Could not update the ticket");

  const snoozeUntilTomorrow = () => {
    const until = new Date();
    until.setDate(until.getDate() + 1);
    until.setHours(9, 0, 0, 0);
    return run(() => customerServiceApi.snoozeConversation(conversation.id, until.toISOString(), "Follow up tomorrow"), "Could not snooze");
  };

  return (
    <header className="shrink-0 border-b border-border bg-muted px-4 py-3 sm:px-5">
      <div className="flex items-start gap-3">
        {onBack ? (
          <button
            type="button"
            onClick={onBack}
            aria-label="Back to inbox"
            className="-ml-1 mt-0.5 rounded-control p-1 text-text-secondary hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus lg:hidden"
          >
            <ArrowLeft size={18} />
          </button>
        ) : null}

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <h1 className="truncate text-[15px] font-semibold text-foreground">
              {customer?.name || customer?.email || "Unknown customer"}
            </h1>
            {customer?.name && customer.email ? (
              <span className="hidden truncate text-[13px] text-text-secondary sm:inline">{customer.email}</span>
            ) : null}
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px] text-text-secondary">
            {state ? <ToneChip tone={state.tone}><span title={state.description}>{state.label}</span></ToneChip> : null}
            {insight?.intent ? <span className="text-foreground">{humanize(insight.intent)}</span> : null}
            {priority === "high" || priority === "urgent" ? (
              <span className={priority === "urgent" ? "text-danger" : "text-warning"}>{humanize(priority)} priority</span>
            ) : null}
            <span>{ticket?.assigned_to ? "Assigned" : "Unassigned"}</span>
            <span>{humanize(conversation.channel)}</span>
            {openSla ? (
              <span className={openSla.breached_at ? "text-danger" : undefined}>
                {openSla.breached_at ? "Response target missed" : `Respond by ${formatDay(openSla.due_at)} ${formatTime(openSla.due_at)}`}
              </span>
            ) : null}
            {snoozedUntil ? <span>Snoozed until {formatDay(snoozedUntil)} {formatTime(snoozedUntil)}</span> : null}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {ticket ? (
            <Menu.Root>
              <Menu.Trigger className="inline-flex h-8 items-center gap-1 rounded-control border border-border bg-surface px-2.5 text-[13px] font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
                {humanize(ticket.status)}
                <ChevronDown size={14} aria-hidden />
              </Menu.Trigger>
              <Menu.Portal>
                <Menu.Content align="end" sideOffset={4} className={menuContent}>
                  <Menu.Label className="px-2 py-1 text-[11px] font-semibold text-text-secondary">Assignee</Menu.Label>
                  <Menu.Item className={menuItem} onSelect={() => void updateTicket("assigned_to", null)}>
                    <Check size={14} className={cn(!ticket.assigned_to ? "opacity-100" : "opacity-0")} aria-hidden />
                    Unassigned
                  </Menu.Item>
                  {agents.map((agent) => (
                    <Menu.Item key={agent.agent_user_id} className={menuItem} onSelect={() => void updateTicket("assigned_to", agent.agent_user_id)}>
                      <Check size={14} className={cn(ticket.assigned_to === agent.agent_user_id ? "opacity-100" : "opacity-0")} aria-hidden />
                      {agent.display_name || agent.email || "Agent"}
                    </Menu.Item>
                  ))}
                  <Menu.Separator className="my-1 h-px bg-border" />
                  <Menu.Label className="px-2 py-1 text-[11px] font-semibold text-text-secondary">Status</Menu.Label>
                  {STATUSES.map((status) => (
                    <Menu.Item key={status} className={menuItem} onSelect={() => void updateTicket("status", status)}>
                      <Check size={14} className={cn(lower(ticket.status) === status ? "opacity-100" : "opacity-0")} aria-hidden />
                      {humanize(status)}
                    </Menu.Item>
                  ))}
                  <Menu.Separator className="my-1 h-px bg-border" />
                  <Menu.Label className="px-2 py-1 text-[11px] font-semibold text-text-secondary">Priority</Menu.Label>
                  {PRIORITIES.map((value) => (
                    <Menu.Item key={value} className={menuItem} onSelect={() => void updateTicket("priority", value)}>
                      <Check size={14} className={cn(priority === value ? "opacity-100" : "opacity-0")} aria-hidden />
                      {humanize(value)}
                    </Menu.Item>
                  ))}
                </Menu.Content>
              </Menu.Portal>
            </Menu.Root>
          ) : null}

          <button
            type="button"
            onClick={onOpenContext}
            className="inline-flex h-8 items-center gap-1.5 rounded-control border border-border bg-surface px-2.5 text-[13px] font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus xl:hidden"
          >
            <PanelRight size={15} aria-hidden />
            <span className="hidden sm:inline">Customer &amp; order</span>
          </button>

          <Menu.Root>
            <Menu.Trigger
              aria-label="More actions"
              className="inline-flex h-8 w-8 items-center justify-center rounded-control text-text-secondary hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <Ellipsis size={16} />
            </Menu.Trigger>
            <Menu.Portal>
              <Menu.Content align="end" sideOffset={4} className={menuContent}>
                {snoozedUntil ? (
                  <Menu.Item className={menuItem} onSelect={() => void run(() => customerServiceApi.wakeConversation(conversation.id), "Could not wake the conversation")}>
                    Wake up now
                  </Menu.Item>
                ) : (
                  <Menu.Item className={menuItem} onSelect={() => void snoozeUntilTomorrow()}>
                    Snooze until tomorrow 9:00
                  </Menu.Item>
                )}
                <Menu.Item className={menuItem} onSelect={() => setRunOpen(true)}>
                  Run a workflow…
                </Menu.Item>
                <Menu.Separator className="my-1 h-px bg-border" />
                <Menu.Item className={cn(menuItem, "text-danger")} onSelect={() => setConfirmDelete(true)}>
                  Delete conversation
                </Menu.Item>
              </Menu.Content>
            </Menu.Portal>
          </Menu.Root>
        </div>
      </div>

      {error ? <p role="alert" className="mt-2 text-[12.5px] text-danger">{error}</p> : null}

      {runOpen ? <RunWorkflowDialog conversationId={conversation.id} open={runOpen} onOpenChange={setRunOpen} /> : null}

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this conversation?"
        description="The conversation and its messages are removed from Tajeran. This can't be undone."
        confirmLabel="Delete conversation"
        tone="danger"
        busy={deleting}
        onConfirm={() => {
          onDelete();
          setConfirmDelete(false);
        }}
      />
    </header>
  );
}
