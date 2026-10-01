"use client";

import { FormEvent, useEffect, useState } from "react";
import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { ProductNotice, ProductPanel } from "@/ui/product";
import { workspaceApi, type Workspace } from "@/domains/workspace/api/workspace";
import { SettingsTabs } from "@/domains/workspace/SettingsTabs";

const DAYS = [
  { key: "mon", label: "Monday" },
  { key: "tue", label: "Tuesday" },
  { key: "wed", label: "Wednesday" },
  { key: "thu", label: "Thursday" },
  { key: "fri", label: "Friday" },
  { key: "sat", label: "Saturday" },
  { key: "sun", label: "Sunday" },
];

type DayHours = { open: boolean; start: string; end: string };
type Window = { start: string; end: string };

// One opening period per day; the first saved period is shown.
function weekFrom(weekly: Record<string, Window[]> | undefined): Record<string, DayHours> {
  return Object.fromEntries(
    DAYS.map(({ key }) => {
      const first = weekly?.[key]?.[0];
      return [key, { open: Boolean(first), start: first?.start ?? "09:00", end: first?.end ?? "17:00" }];
    }),
  );
}

const timezones = ["UTC", "Europe/London", "Europe/Berlin", "Asia/Tehran", "America/New_York", "America/Los_Angeles"];

export default function SettingsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [form, setForm] = useState({ name: "", business_name: "", support_email: "", timezone: "UTC", business_hours_mode: "24_7", reply_target_minutes: "" });
  const [week, setWeek] = useState<Record<string, DayHours>>(weekFrom(undefined));
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setLoading(true);
      const current = await workspaceApi.current();
      setWorkspace(current);
      setForm({ name: current.name ?? "", business_name: current.business_name ?? "", support_email: current.support_email ?? "", timezone: current.timezone ?? "UTC", business_hours_mode: String(current.business_hours?.mode || "24_7"), reply_target_minutes: current.business_hours?.reply_target_minutes ? String(current.business_hours.reply_target_minutes) : "" });
      setWeek(weekFrom(current.business_hours?.weekly_hours as Record<string, Window[]> | undefined));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load workspace settings.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load().catch(() => {}); }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!workspace) return;
    try {
      setSaving(true);
      setStatus(null);
      const { reply_target_minutes: _previousTarget, ...calendar } = workspace.business_hours || {};
      const businessHours = {
        ...calendar,
        mode: form.business_hours_mode,
        weekly_hours: Object.fromEntries(
          DAYS.filter(({ key }) => week[key].open).map(({ key }) => [key, [{ start: week[key].start, end: week[key].end }]]),
        ),
        ...(form.reply_target_minutes ? { reply_target_minutes: Number(form.reply_target_minutes) } : {}),
      };
      const updated = await workspaceApi.update(workspace.id, {
        name: form.name,
        business_name: form.business_name,
        support_email: form.support_email,
        timezone: form.timezone,
        business_hours: businessHours,
      });
      setWorkspace(updated);
      setStatus("Workspace settings saved.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save workspace settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppContainer>
      <PageHeader eyebrow="Workspace" title="Settings" description="Configure the identity, working hours, and people behind your customer-support workspace." />
      <SettingsTabs />
      {status && <ProductNotice>{status}</ProductNotice>}
      {loading ? <ProductPanel title="Loading workspace" description="Reading your workspace settings."><div className="h-12" /></ProductPanel> : (
        <div className="max-w-2xl">
          <ProductPanel title="Workspace profile" description="These details are used in support replies and customer-facing channels.">
            <form onSubmit={save} className="space-y-4">
              <label className="block text-sm font-semibold text-foreground">Workspace name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-2 h-11 w-full rounded-xl border border-border px-3 font-normal outline-none focus:border-focus" required /></label>
              <label className="block text-sm font-semibold text-foreground">Business name<input value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} placeholder="Shown to customers" className="mt-2 h-11 w-full rounded-xl border border-border px-3 font-normal outline-none focus:border-focus" /></label>
              <label className="block text-sm font-semibold text-foreground">Support email<input type="email" value={form.support_email} onChange={(e) => setForm({ ...form, support_email: e.target.value })} placeholder="support@example.com" className="mt-2 h-11 w-full rounded-xl border border-border px-3 font-normal outline-none focus:border-focus" /></label>
              <label className="block text-sm font-semibold text-foreground">Timezone<select value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })} className="mt-2 h-11 w-full rounded-xl border border-border bg-surface px-3 font-normal outline-none focus:border-focus">{timezones.map((timezone) => <option key={timezone}>{timezone}</option>)}</select></label>
              <label className="block text-sm font-semibold text-foreground">Business hours<select value={form.business_hours_mode} onChange={(e) => setForm({ ...form, business_hours_mode: e.target.value })} className="mt-2 h-11 w-full rounded-xl border border-border bg-surface px-3 font-normal outline-none focus:border-focus"><option value="24_7">24/7 support</option><option value="scheduled">Weekly schedule</option></select></label>
              {form.business_hours_mode === "scheduled" ? (
                <fieldset className="space-y-2">
                  <legend className="sr-only">Opening hours</legend>
                  {DAYS.map(({ key, label }) => (
                    <div key={key} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                      <label className="flex w-32 items-center gap-2 text-foreground">
                        <input type="checkbox" checked={week[key].open} onChange={(e) => setWeek({ ...week, [key]: { ...week[key], open: e.target.checked } })} className="h-4 w-4" />
                        {label}
                      </label>
                      {week[key].open ? (
                        <span className="flex items-center gap-2">
                          <input type="time" aria-label={`${label} opens`} value={week[key].start} onChange={(e) => setWeek({ ...week, [key]: { ...week[key], start: e.target.value } })} className="h-9 rounded-xl border border-border px-2" required />
                          <span className="text-text-secondary">to</span>
                          <input type="time" aria-label={`${label} closes`} value={week[key].end} onChange={(e) => setWeek({ ...week, [key]: { ...week[key], end: e.target.value } })} className="h-9 rounded-xl border border-border px-2" required />
                        </span>
                      ) : (
                        <span className="text-text-secondary">Closed</span>
                      )}
                    </div>
                  ))}
                </fieldset>
              ) : null}
              <label className="block text-sm font-semibold text-foreground">First reply target (minutes)<input type="number" min={1} max={10080} step={1} value={form.reply_target_minutes} onChange={(e) => setForm({ ...form, reply_target_minutes: e.target.value })} placeholder="No target" className="mt-2 h-11 w-full rounded-xl border border-border px-3 font-normal outline-none focus:border-focus" /><span className="mt-1 block text-xs font-normal text-text-secondary">Counted during business hours. Live, the Inbox and Desk show conversations close to or past this target. Leave empty for no target.</span></label>
              <button type="submit" disabled={saving} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{saving ? "Saving..." : "Save workspace"}</button>
            </form>
          </ProductPanel>
        </div>
      )}
    </AppContainer>
  );
}
