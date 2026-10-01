"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";

import {
  AutomationReport,
  SatisfactionReport,
  SpeedReport,
  TicketsReport,
  useInsights,
} from "@/domains/customer-service/desk/DeskReports";

const tabs = [
  { id: "automation", label: "Automation", Report: AutomationReport },
  { id: "tickets", label: "Tickets", Report: TicketsReport },
  { id: "speed", label: "Speed", Report: SpeedReport },
  { id: "satisfaction", label: "Satisfaction", Report: SatisfactionReport },
];

export default function DashboardPage() {
  const [tab, setTab] = useState("automation");
  const [days, setDays] = useState(30);
  const { data, error, loading, reload } = useInsights(days);
  const Report = tabs.find((item) => item.id === tab)!.Report;

  return (
    <div className="min-h-full bg-[#f8f9fa] text-foreground">
      <main className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Below lg the app header already shows the page title. */}
          <h1 className="hidden text-2xl font-semibold tracking-tight lg:block">Desk</h1>
          <div className="flex items-center gap-2">
            <select
              aria-label="Time period"
              value={days}
              onChange={(event) => setDays(Number(event.target.value))}
              className="h-9 rounded border border-border bg-surface px-2 text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              type="button"
              onClick={reload}
              disabled={loading}
              className="inline-flex h-9 items-center gap-1.5 rounded border border-border bg-surface px-3 text-sm hover:bg-muted"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
            </button>
          </div>
        </div>
        <nav className="mt-4 flex overflow-x-auto border-b border-border" aria-label="Desk reports" role="tablist">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              onClick={() => setTab(item.id)}
              className={`whitespace-nowrap border-b-2 px-3 py-3 text-sm ${tab === item.id ? "border-primary font-semibold text-foreground" : "border-transparent text-text-secondary hover:text-foreground"}`}
            >
              {item.label}
            </button>
          ))}
        </nav>
        {error ? <p role="alert" className="mt-5 text-sm text-danger">{error}</p> : null}
        {data ? (
          <>
            {data.automation_previous.total + data.speed_previous.first_reply.conversations + data.rating_previous.responses === 0 ? (
              <p className="mt-4 text-xs text-text-secondary">No earlier data to compare.</p>
            ) : null}
            <Report data={data} />
          </>
        ) : error ? null : (
          <div className="mt-5 h-40 animate-pulse rounded bg-muted" />
        )}
      </main>
    </div>
  );
}
