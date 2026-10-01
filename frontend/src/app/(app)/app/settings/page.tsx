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

const TIMEZONES = ["UTC", "Europe/London", "Europe/Berlin", "Asia/Tehran", "America/New_York", "America/Los_Angeles"];

const labelClass = "block text-sm font-semibold text-foreground";
const fieldClass = "mt-2 h-11 w-full rounded-xl border border-border bg-surface px-3 font-normal outline-none focus:border-focus";
const timeClass = "h-9 rounded-xl border border-border px-2";

type DayHours = { open: boolean; start: string; end: string };
type Window = { start: string; end: string };
type Week = Record<string, DayHours>;

type Form = {
  name: string;
  business_name: string;
  support_email: string;
  timezone: string;
  business_hours_mode: string;
  reply_target_minutes: string;
};

const EMPTY_FORM: Form = {
  name: "",
  business_name: "",
  support_email: "",
  timezone: "UTC",
  business_hours_mode: "24_7",
  reply_target_minutes: "",
};

// One opening period per day; the first saved period is shown.
function weekFrom(weekly: Record<string, Window[]> | undefined): Week {
  return Object.fromEntries(
    DAYS.map(({ key }) => {
      const first = weekly?.[key]?.[0];
      return [key, { open: Boolean(first), start: first?.start ?? "09:00", end: first?.end ?? "17:00" }];
    }),
  );
}

function formFrom(workspace: Workspace): Form {
  const hours = workspace.business_hours;
  return {
    name: workspace.name ?? "",
    business_name: workspace.business_name ?? "",
    support_email: workspace.support_email ?? "",
    timezone: workspace.timezone ?? "UTC",
    business_hours_mode: String(hours?.mode || "24_7"),
    reply_target_minutes: hours?.reply_target_minutes ? String(hours.reply_target_minutes) : "",
  };
}

// The calendar to save: the stored one with this form's mode, opening hours and target.
function businessHoursFrom(workspace: Workspace, form: Form, week: Week) {
  const { reply_target_minutes: _previousTarget, ...calendar } = workspace.business_hours || {};
  return {
    ...calendar,
    mode: form.business_hours_mode,
    weekly_hours: Object.fromEntries(
      DAYS.filter(({ key }) => week[key].open).map(({ key }) => [key, [{ start: week[key].start, end: week[key].end }]]),
    ),
    ...(form.reply_target_minutes ? { reply_target_minutes: Number(form.reply_target_minutes) } : {}),
  };
}

function OpeningHours({ week, onChange }: { week: Week; onChange: (week: Week) => void }) {
  const setDay = (key: string, values: Partial<DayHours>) => onChange({ ...week, [key]: { ...week[key], ...values } });

  return (
    <fieldset className="space-y-2">
      <legend className="sr-only">Opening hours</legend>
      {DAYS.map(({ key, label }) => (
        <div key={key} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <label className="flex w-32 items-center gap-2 text-foreground">
            <input
              type="checkbox"
              checked={week[key].open}
              onChange={(e) => setDay(key, { open: e.target.checked })}
              className="h-4 w-4"
            />
            {label}
          </label>
          {week[key].open ? (
            <span className="flex items-center gap-2">
              <input
                type="time"
                aria-label={`${label} opens`}
                value={week[key].start}
                onChange={(e) => setDay(key, { start: e.target.value })}
                className={timeClass}
                required
              />
              <span className="text-text-secondary">to</span>
              <input
                type="time"
                aria-label={`${label} closes`}
                value={week[key].end}
                onChange={(e) => setDay(key, { end: e.target.value })}
                className={timeClass}
                required
              />
            </span>
          ) : (
            <span className="text-text-secondary">Closed</span>
          )}
        </div>
      ))}
    </fieldset>
  );
}

export default function SettingsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [form, setForm] = useState<Form>(EMPTY_FORM);
  const [week, setWeek] = useState<Week>(weekFrom(undefined));
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const set = (values: Partial<Form>) => setForm({ ...form, ...values });

  useEffect(() => {
    workspaceApi
      .current()
      .then((current) => {
        setWorkspace(current);
        setForm(formFrom(current));
        setWeek(weekFrom(current.business_hours?.weekly_hours as Record<string, Window[]> | undefined));
      })
      .catch((error) => setStatus(error instanceof Error ? error.message : "Could not load workspace settings."))
      .finally(() => setLoading(false));
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!workspace) return;
    try {
      setSaving(true);
      setStatus(null);
      const updated = await workspaceApi.update(workspace.id, {
        name: form.name,
        business_name: form.business_name,
        support_email: form.support_email,
        timezone: form.timezone,
        business_hours: businessHoursFrom(workspace, form, week),
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
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Configure the identity, working hours, and people behind your customer-support workspace."
      />
      <SettingsTabs />
      {status && <ProductNotice>{status}</ProductNotice>}
      {loading ? (
        <ProductPanel title="Loading workspace" description="Reading your workspace settings.">
          <div className="h-12" />
        </ProductPanel>
      ) : (
        <div className="max-w-2xl">
          <ProductPanel
            title="Workspace profile"
            description="These details are used in support replies and customer-facing channels."
          >
            <form onSubmit={save} className="space-y-4">
              <label className={labelClass}>
                Workspace name
                <input value={form.name} onChange={(e) => set({ name: e.target.value })} className={fieldClass} required />
              </label>
              <label className={labelClass}>
                Business name
                <input
                  value={form.business_name}
                  onChange={(e) => set({ business_name: e.target.value })}
                  placeholder="Shown to customers"
                  className={fieldClass}
                />
              </label>
              <label className={labelClass}>
                Support email
                <input
                  type="email"
                  value={form.support_email}
                  onChange={(e) => set({ support_email: e.target.value })}
                  placeholder="support@example.com"
                  className={fieldClass}
                />
              </label>
              <label className={labelClass}>
                Timezone
                <select value={form.timezone} onChange={(e) => set({ timezone: e.target.value })} className={fieldClass}>
                  {TIMEZONES.map((timezone) => (
                    <option key={timezone}>{timezone}</option>
                  ))}
                </select>
              </label>
              <label className={labelClass}>
                Business hours
                <select
                  value={form.business_hours_mode}
                  onChange={(e) => set({ business_hours_mode: e.target.value })}
                  className={fieldClass}
                >
                  <option value="24_7">24/7 support</option>
                  <option value="scheduled">Weekly schedule</option>
                </select>
              </label>
              {form.business_hours_mode === "scheduled" ? <OpeningHours week={week} onChange={setWeek} /> : null}
              <label className={labelClass}>
                First reply target (minutes)
                <input
                  type="number"
                  min={1}
                  max={10080}
                  step={1}
                  value={form.reply_target_minutes}
                  onChange={(e) => set({ reply_target_minutes: e.target.value })}
                  placeholder="No target"
                  className={fieldClass}
                />
                <span className="mt-1 block text-xs font-normal text-text-secondary">
                  Counted during business hours. Live, the Inbox and Desk show conversations close to or past this
                  target. Leave empty for no target.
                </span>
              </label>
              <button
                type="submit"
                disabled={saving}
                className="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
              >
                {saving ? "Saving..." : "Save workspace"}
              </button>
            </form>
          </ProductPanel>
        </div>
      )}
    </AppContainer>
  );
}
