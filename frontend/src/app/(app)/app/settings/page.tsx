"use client";

import { FormEvent, useEffect, useState } from "react";
import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { ProductNotice, ProductPanel } from "@/ui/product";
import { workspaceApi, type Workspace, type WorkspaceMember } from "@/domains/workspace/api/workspace";
import { SettingsTabs } from "@/domains/workspace/SettingsTabs";

const timezones = ["UTC", "Europe/London", "Europe/Berlin", "Asia/Tehran", "America/New_York", "America/Los_Angeles"];

export default function SettingsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [team, setTeam] = useState<WorkspaceMember[]>([]);
  const [form, setForm] = useState({ name: "", business_name: "", support_email: "", timezone: "UTC", business_hours_mode: "24_7" });
  const [invite, setInvite] = useState({ email: "", role: "agent" });
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setLoading(true);
      const current = await workspaceApi.current();
      const roster = await workspaceApi.team(current.id).catch(() => []);
      setWorkspace(current);
      setTeam(roster);
      setForm({ name: current.name ?? "", business_name: current.business_name ?? "", support_email: current.support_email ?? "", timezone: current.timezone ?? "UTC", business_hours_mode: String(current.business_hours?.mode || "24_7") });
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
      const updated = await workspaceApi.update(workspace.id, {
        name: form.name,
        business_name: form.business_name,
        support_email: form.support_email,
        timezone: form.timezone,
        business_hours: {
          ...(workspace.business_hours || {}),
          mode: form.business_hours_mode,
        },
      });
      setWorkspace(updated);
      setStatus("Workspace settings saved.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save workspace settings.");
    } finally {
      setSaving(false);
    }
  }

  async function sendInvite(event: FormEvent) {
    event.preventDefault();
    if (!workspace || !invite.email.trim()) return;
    try {
      setStatus(null);
      await workspaceApi.invite(workspace.id, invite);
      setInvite({ email: "", role: "agent" });
      setStatus("Invitation sent.");
      setTeam(await workspaceApi.team(workspace.id));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not invite team member.");
    }
  }

  return (
    <AppContainer>
      <PageHeader eyebrow="Workspace" title="Settings" description="Configure the identity, working hours, and people behind your customer-support workspace." />
      <SettingsTabs />
      {status && <ProductNotice>{status}</ProductNotice>}
      {loading ? <ProductPanel title="Loading workspace" description="Reading your workspace settings and team roster."><div className="h-12" /></ProductPanel> : (
        <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <ProductPanel title="Workspace profile" description="These details are used in support replies and customer-facing channels.">
            <form onSubmit={save} className="space-y-4">
              <label className="block text-sm font-semibold text-slate-800">Workspace name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-3 font-normal outline-none focus:border-slate-400" required /></label>
              <label className="block text-sm font-semibold text-slate-800">Business name<input value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} placeholder="Shown to customers" className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-3 font-normal outline-none focus:border-slate-400" /></label>
              <label className="block text-sm font-semibold text-slate-800">Support email<input type="email" value={form.support_email} onChange={(e) => setForm({ ...form, support_email: e.target.value })} placeholder="support@example.com" className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-3 font-normal outline-none focus:border-slate-400" /></label>
              <label className="block text-sm font-semibold text-slate-800">Timezone<select value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })} className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 font-normal outline-none focus:border-slate-400">{timezones.map((timezone) => <option key={timezone}>{timezone}</option>)}</select></label>
              <label className="block text-sm font-semibold text-slate-800">Business hours<select value={form.business_hours_mode} onChange={(e) => setForm({ ...form, business_hours_mode: e.target.value })} className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 font-normal outline-none focus:border-slate-400"><option value="24_7">24/7 support</option><option value="weekly">Weekly schedule</option></select></label>
              <button type="submit" disabled={saving} className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{saving ? "Saving..." : "Save workspace"}</button>
            </form>
          </ProductPanel>
          <ProductPanel title="Team" description="Invite agents who can reply, route conversations, and review approvals.">
            <form onSubmit={sendInvite} className="space-y-3"><input type="email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} placeholder="agent@example.com" className="h-11 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-slate-400" required /><div className="flex gap-2"><select value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })} className="h-11 min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-sm"><option value="agent">Agent</option><option value="manager">Manager</option><option value="admin">Admin</option></select><button type="submit" className="rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white">Invite</button></div></form>
            <div className="mt-5 space-y-2">{team.length === 0 ? <p className="text-sm text-slate-500">No team members yet.</p> : team.map((member) => <div key={member.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5"><div className="min-w-0"><div className="truncate text-sm font-semibold text-slate-900">{member.display_name || member.email}</div><div className="text-xs capitalize text-slate-500">{member.state || member.status}</div></div><span className="rounded-full bg-white px-2 py-1 text-xs font-semibold capitalize text-slate-600">{member.role}</span></div>)}</div>
          </ProductPanel>
        </div>
      )}
    </AppContainer>
  );
}
