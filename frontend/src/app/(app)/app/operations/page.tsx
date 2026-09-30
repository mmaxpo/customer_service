"use client";

import { useEffect, useState } from "react";
import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { ProductNotice, ProductPanel, ProductStatCard } from "@/ui/product";
import { customerServiceApi } from "@/domains/customer-service/api/customer-service";

type Analytics = {
  total_customers?: number;
  total_conversations?: number;
  open_tickets?: number;
  pending_tickets?: number;
  closed_tickets?: number;
  urgent_tickets?: number;
  open_sla_breaches?: number;
};

export default function OperationsPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [violations, setViolations] = useState<any[]>([]);
  const [workload, setWorkload] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkingSla, setCheckingSla] = useState(false);

  async function load() {
    try {
      setLoading(true);
      const [summary, breaches, teamWorkload, logs] = await Promise.all([
        customerServiceApi.analytics(),
        customerServiceApi.slaViolations().catch(() => []),
        customerServiceApi.workloadReport().catch(() => []),
        customerServiceApi.auditLogs(25).catch(() => []),
      ]);
      setAnalytics(summary);
      setViolations(breaches);
      setWorkload(teamWorkload);
      setAudit(logs);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load operations data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load().catch(() => {}); }, []);

  async function checkSla() {
    try {
      setCheckingSla(true);
      setStatus(null);
      await customerServiceApi.checkSLA();
      await load();
      setStatus("SLA check completed.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not check SLA status.");
    } finally {
      setCheckingSla(false);
    }
  }

  return (
    <AppContainer>
      <PageHeader eyebrow="Operations" title="Support performance" description="See whether Tajeran is resolving conversations, meeting response targets, and keeping a trustworthy action history." actions={<button onClick={checkSla} disabled={checkingSla} className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{checkingSla ? "Checking..." : "Check SLA now"}</button>} />
      {status && <ProductNotice>{status}</ProductNotice>}
      {loading ? <ProductPanel title="Loading operations" description="Gathering support, SLA, and audit data."><div className="h-12" /></ProductPanel> : (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <ProductStatCard label="Conversations" value={analytics?.total_conversations ?? 0} description="Total support volume" />
            <ProductStatCard label="Open tickets" value={analytics?.open_tickets ?? 0} description={`${analytics?.urgent_tickets ?? 0} urgent`} />
            <ProductStatCard label="Resolved" value={analytics?.closed_tickets ?? 0} description="Closed tickets" />
            <ProductStatCard label="SLA breaches" value={analytics?.open_sla_breaches ?? violations.length} description="Needs attention" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <ProductPanel title="SLA attention" description="Breaches are visible here so a manager can act before they become a customer problem.">
              {violations.length === 0 ? <p className="rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-800">No open SLA breaches.</p> : <div className="space-y-2">{violations.slice(0, 10).map((item) => <div key={item.id} className="rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm"><div className="font-semibold text-slate-900">Ticket {item.ticket_id}</div><div className="mt-1 text-slate-600">{item.target_type} · {item.status} · due {new Date(item.due_at).toLocaleString()}</div></div>)}</div>}
            </ProductPanel>
            <ProductPanel title="Team workload" description="A simple view of open and pending work by assignee.">
              {workload.length === 0 ? <p className="text-sm text-slate-500">No workload data yet.</p> : <div className="space-y-2">{workload.slice(0, 10).map((item) => <div key={item.assigned_to} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5 text-sm"><span className="truncate">{item.assigned_to}</span><span className="font-semibold">{item.open_or_pending_tickets}</span></div>)}</div>}
            </ProductPanel>
          </div>
          <ProductPanel title="Audit trail" description="Recent configuration and customer-service actions recorded by Tajeran.">
            {audit.length === 0 ? <p className="text-sm text-slate-500">No audit events yet.</p> : <div className="space-y-2">{audit.map((item) => <div key={item.id} className="flex flex-col gap-1 rounded-xl border border-slate-100 bg-slate-50 p-3 text-sm sm:flex-row sm:items-center sm:justify-between"><div><span className="font-semibold text-slate-900">{item.action || "Action"}</span><span className="ml-2 text-slate-500">{item.entity_type || "workspace"}</span></div><time className="text-xs text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleString() : "—"}</time></div>)}</div>}
          </ProductPanel>
        </>
      )}
    </AppContainer>
  );
}
