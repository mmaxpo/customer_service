import { Workflow } from "lucide-react";

import { cn } from "@/platform/utils";
import { TajeranMark } from "@/ui/brand/TajeranMark";

import { initials } from "./format";
import type { Actor, Tone } from "./timeline";

const toneClass: Record<Tone, string> = {
  neutral: "border-border bg-muted text-text-secondary",
  attention: "border-warning/30 bg-warning/10 text-warning",
  failure: "border-danger/30 bg-danger/10 text-danger",
  commerce: "border-commerce-accent/30 bg-commerce-accent/10 text-commerce-accent",
};

export function ToneChip({ tone, children, className }: { tone: Tone; children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-px text-[11px] font-medium leading-4", toneClass[tone], className)}>
      {children}
    </span>
  );
}

export function ActorAvatar({ actor, name, size = 24 }: { actor: Actor; name?: string | null; size?: number }) {
  if (actor === "tajeran") return <TajeranMark variant="actor" size={size} title="Tajeran" />;

  const base = "inline-flex shrink-0 items-center justify-center rounded-full text-[10px] font-semibold";
  const style = { width: size, height: size };

  if (actor === "workflow") {
    return (
      <span className={cn(base, "border border-border bg-surface text-text-secondary")} style={style} title="Workflow">
        <Workflow size={size * 0.55} strokeWidth={1.75} aria-hidden />
      </span>
    );
  }
  if (actor === "teammate") {
    return (
      <span className={cn(base, "bg-primary/10 text-primary")} style={style} title="Teammate">
        {name ? initials(name) : "You"}
      </span>
    );
  }
  if (actor === "customer") {
    return (
      <span className={cn(base, "bg-muted text-foreground")} style={style} title={name ?? "Customer"}>
        {initials(name)}
      </span>
    );
  }
  return <span className="mx-[9px] block h-1.5 w-1.5 shrink-0 rounded-full bg-border" aria-hidden />;
}

export function Section({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="border-b border-border px-4 py-3.5 last:border-b-0">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-[12px] font-semibold text-text-secondary">{title}</h3>
        {action}
      </div>
      {children}
    </section>
  );
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-0.5 text-[13px]">
      <dt className="shrink-0 text-text-secondary">{label}</dt>
      <dd className="min-w-0 text-right text-foreground">{children}</dd>
    </div>
  );
}
