import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { MessageCircle } from "lucide-react";

export function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.07] p-4">
      <Icon size={18} className="text-emerald-200" />
      <div className="mt-3 text-xs font-bold uppercase tracking-[0.15em] text-slate-400">{label}</div>
      <div className="mt-1 text-sm font-black text-white">{value}</div>
    </div>
  );
}

export function Status({
  active,
  label,
}: {
  active: boolean;
  label: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
      <span className="text-sm text-slate-200">{label}</span>
      <span className={["h-2.5 w-2.5 rounded-full", active ? "bg-emerald-400" : "bg-slate-500"].join(" ")} />
    </div>
  );
}

export function Toggle({
  title,
  description,
  checked,
  onChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div>
        <div className="font-black text-slate-950">{title}</div>
        <div className="mt-1 text-sm leading-6 text-slate-500">{description}</div>
      </div>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-5 w-5" />
    </label>
  );
}

export function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-2">
      <span className="text-sm font-black text-slate-800">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-12 w-full rounded-2xl border border-slate-300 bg-white px-4 text-sm text-slate-950 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100"
      />
    </label>
  );
}

export function Panel({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-[2rem] border border-slate-200 bg-white p-5 shadow-xl shadow-slate-200/70">
      <div className="mb-5 flex items-center gap-4">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white">
          <Icon size={20} />
        </div>
        <h2 className="text-xl font-black text-slate-950">{title}</h2>
      </div>
      {children}
    </div>
  );
}

export function Bubble({
  children,
  mine = false,
}: {
  children: ReactNode;
  mine?: boolean;
}) {
  return (
    <div
      className={[
        "max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-6",
        mine ? "ml-auto rounded-br-md bg-slate-950 text-white" : "mr-auto rounded-bl-md bg-white text-slate-700 shadow-sm",
      ].join(" ")}
    >
      {children}
    </div>
  );
}

export { MessageCircle };
